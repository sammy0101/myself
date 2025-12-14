export default (proxies) => {
  return proxies.map(p => {
    // 修改伺服器地址
    p.server = "hello.cf.090227.xyz";
    return p;
  });
};
