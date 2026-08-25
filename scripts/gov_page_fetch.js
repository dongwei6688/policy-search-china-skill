// gov.cn 政策详情页全文提取器（playwright 渲染）
// 用法: node gov_page_fetch.js "https://www.gov.cn/zhengce/zhengceku/xxx.htm"
// 输出: JSON {title, doc_number, issuer, date, content}
const { chromium } = require('playwright');

const url = process.argv[2] || '';

(async () => {
  let browser = null;
  const launchOpts = [
    { headless: true, channel: 'chrome' },
    { headless: true },
  ];
  for (const opts of launchOpts) {
    try {
      browser = await chromium.launch(opts);
      break;
    } catch (e) {
      browser = null;
    }
  }
  if (!browser) {
    console.log(JSON.stringify({ success: false, error: 'no-browser' }));
    return;
  }
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 25000 });
    await page.waitForSelector('.pages_content', { timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(2000);
    const data = await page.evaluate(() => {
      const contentEl = document.querySelector('.pages_content');
      const content = contentEl ? contentEl.innerText.trim() : '';
      // 从页面信息区提取元信息（标题/发文机关/发文字号/成文日期）
      const bodyText = document.body ? document.body.innerText : '';
      const grab = (label) => {
        const re = new RegExp(label + '[：:]\\s*([^\\n\\t]{3,120})');
        const m = bodyText.match(re);
        return m ? m[1].trim() : '';
      };
      const title = grab('标\\s*题') || (content.split('\n')[0] || '');
      return {
        title,
        doc_number: grab('发文字号'),
        issuer: grab('发文机关'),
        date: grab('成文日期'),
        content,
      };
    });
    console.log(JSON.stringify({ success: true, ...data }));
  } catch (e) {
    console.log(JSON.stringify({ success: false, error: String(e).slice(0, 200) }));
  } finally {
    await browser.close();
  }
})();
