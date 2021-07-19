# Leetcode parser

## 說明
爬取leetcode題目 & 讚數 & 分類 以供刷題參考  
使用時請下載自己Chrome對應版本的chromedriver.exe放到目錄下 https://chromedriver.chromium.org/downloads  
檢視資料可用jupyter notebook開啟`view.ipynb`


## 流程
分三個步驟:
1. 先把所有題目跟url爬下來。產出為`questions.csv`  
2. 分別點開每個題目的url去補評分, 此步驟耗時最長。產出為`questions_with_rating.csv`  
3. 爬取題目分類幫題目上標籤。產出為`questions_with_tag.csv`  
