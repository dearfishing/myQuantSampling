import numpy as np
import pandas as pd
import matplotlib.pyplot as plt



dataPath = 'Data2\\'


Stock_Conversion_Data={'300070':[['2016-05-13', 2.47]],
'601166':[['2016-06-03', 1.03]]}

def stockConversion(data,conversion,dtCol):
    pxLikeCol = [col for col in data.columns if 'mid' in col]
    volumLikeCol = [col for col in data.columns if ('imbl' in col) and ('Cnt' not in col)]
    for item in conversion:
        [dt,factor]=item
        data.ix[(data[dtCol] <= pd.to_datetime(dt + 'T23:00:00')), pxLikeCol] = (data.ix[(data[dtCol] <= pd.to_datetime(
            dt + 'T23:00:00')), pxLikeCol]) / factor
        data.ix[(data[dtCol] <= pd.to_datetime(dt + 'T23:00:00')), volumLikeCol] = (data.ix[(data[dtCol] <= pd.to_datetime(
            dt + 'T23:00:00')), volumLikeCol]) * factor
    return data

def setupData(rvSymbols,symbolTarget,quan,path):
    symbolList = [item for key in rvSymbols for item in list(rvSymbols[key].keys())]+[symbolTarget]
    data = pd.read_csv(path+'\\'+dataPath+symbolTarget+'.csv')
    combined=pd.DataFrame({'barTime':pd.to_datetime(data.barTime),
                           'mid_'+symbolTarget:data.mid,
                           'mid5_'+symbolTarget:data.midEma5,
                           'mid10_'+symbolTarget:data.midEma10,
                           'mid20_'+symbolTarget:data.midEma20,
                           'imbl': data.imbl,
                           'imbl3': data.imbl3,
                           'imbl3Chg':data.imbl3 - data.imbl3_30,
                           'imblThrough': data.imblThrough,
                           'imblSpread': data.imbl - data.imblThrough,
                           'imblCnt3': data.imblCnt3,
                           'imblCnt3Chg':data.imblCnt3 - data.imblCnt3_30,
                           'imblCnt': data.imblCnt,
                           'imblCntThrough': data.imblCntThrough,
                           'imblCntSpread': data.imblCnt - data.imblCntThrough,
                           'imblCncl': data.imblCncl,
                           'imblCnclChg':data.imblCncl - data.imblCncl_30
                           })
    if symbolTarget in Stock_Conversion_Data.keys():
        combined = stockConversion(combined,Stock_Conversion_Data[symbolTarget],'barTime')

    rawFeature = combined.columns - ['barTime','mid','flattener','date','timeStepCheck']-[col for col in combined.columns if ('future' in col)|('feature' in col)|(('pnl' in col)|('mid' in col))]
    for col in rawFeature:
        print(col, np.abs(combined[col]).quantile(quan))
        combined['feature_'+col]=np.tanh(combined[col]/np.abs(combined[col]).quantile(quan))

    for symbol in symbolList:
        if symbol!=symbolTarget:
            data = pd.read_csv(path+'\\'+dataPath + symbol + '.csv')
            data['barTime']=pd.to_datetime(data.barTime)
            if symbol in Stock_Conversion_Data.keys():
                data = stockConversion(data, Stock_Conversion_Data[symbol], 'barTime')

            combined = pd.merge(combined, pd.DataFrame({'mid_' + symbol:data.mid,
                                                        'mid5_' + symbol:data.midEma5,
                                                        'mid10_' + symbol:data.midEma10,
                                                        'mid20_' + symbol:data.midEma20,
                                                        'barTime':data.barTime}),
                                on='barTime', how='left')
    changeColume = 'mid'
    for dataStep in 1,5:
        minuteDelta = dataStep
        combined['timeStepCheck']=combined.barTime.diff(dataStep).shift(-dataStep)
        for symbol in symbolList:
            combined['future_change_'+str(dataStep)+'_'+symbol]=combined[changeColume+'_'+symbol].diff(dataStep).shift(-dataStep)
            combined.ix[combined['timeStepCheck']!=pd.Timedelta(minutes = minuteDelta),'future_change_'+str(dataStep)+'_'+symbol]=np.NaN
            combined['future_nextChange_'+str(dataStep)+'_'+symbol]=combined['future_change_'+str(dataStep)+'_'+symbol].shift(-1)

    for symbol in symbolList:
        combined['midChange_' + symbol] = combined['mid5_'+symbol] - combined['mid10_'+symbol]
        combined['midChange2_' + symbol] = combined['mid5_'+symbol] - 2 * combined['mid10_'+symbol] + combined['mid20_'+symbol]
        combined['feature_midChange_'+symbol] = np.tanh(
            combined['midChange_' + symbol] / np.abs(combined['midChange_' + symbol]).quantile(quan))
        combined['feature_midChange2_' + symbol] = np.tanh(
            combined['midChange2_' + symbol] / np.abs(combined['midChange2_' + symbol]).quantile(quan))

    #get retlative value feature
    for key in rvSymbols.keys():
        comp = rvSymbols[key]
        den = np.sum(list(comp.values()))
        combined['feature_midChange_'+key] = combined[['feature_midChange_'+name for name in comp.keys()]].dot(list(comp.values()))/den
        combined['feature_midChange2_' + key] = combined[['feature_midChang2_' + name for name in comp.keys()]].dot(
            list(comp.values()))
        combined['product'] = combined['feature_midChange_' + key] * combined[
            'feature_midChange_' + symbolTarget]
        combined['absDiff'] = np.abs(combined['feature_midChange_' + key]) - np.abs(
            combined['feature_midChange_' + symbolTarget])
        combined['feature_midChangeOver_' + key] = combined['feature_midChange_' + key]
        combined.ix[(combined['product'] >= 0) & (combined['absDiff'] < 0), 'feature_midChangeOver_' + key] = 0
        combined['feature_midChangeUnder_' + key] = combined['feature_midChange_' + key] - combined[
            'feature_midChangeOver_' + key]
        combined.drop(['feature_midChange_'+name for name in comp.keys()], inplace=True, axis=1)
        combined.drop(['feature_midChange2_' + name for name in comp.keys()], inplace=True, axis=1)



    col='future_change_1_'
    for symbol in symbolList:
        if symbol!=symbolTarget:
            plt.xcorr(combined.dropna()[col+symbolTarget], combined.dropna()[col+symbol].values, normed=True, usevlines=True, maxlags=15)
        plt.title(symbolTarget + '_' + symbol)
        plt.show()
    return combined
