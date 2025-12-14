function main(proxies) {
  return proxies.map(p => {
    p.server = "hello.cf.090227.xyz";
    return p;
  });
}

// 判斷環境，自動選擇導出方式
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
  module.exports = main; // Node.js 環境
} else {
  // ES Module 或其他環境，嘗試透過 global 導出，或利用 Sub-Store 的隱式回傳
  try {
     // 大部分支援 export default 的環境其實也支援直接回傳函數
  } catch(e) {}
}

// 針對 Sub-Store 部分特殊環境 (如 CF Workers)，嘗試使用 export default
// 注意：如果您的編輯器報錯，請忽略，直接提交到 GitHub
export default main;
