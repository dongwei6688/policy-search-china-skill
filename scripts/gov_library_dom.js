// gov.cn 政策库搜索接口 — DOM 提取器（playwright 渲染）
// 用法: node gov_library_dom.js "关键词" [最大页数]
// 输出: JSON {count, entries:[{title, source_url, summary, category, date}]}
const { chromium } = require('playwright');

const keyword = process.argv[2] || '';
const maxPages = Math.max(1, parseInt(process.argv[3] || '1', 10));

(async () => {
  let browser = null;
  // 优先系统 Chrome（真实指纹，可过 WAF），失败回退 playwright 自带内核
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
    console.log(JSON.stringify({ count: 0, entries: [], error: 'no-browser' }));
    return;
  }
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const url = 'https://sousuo.www.gov.cn/zcwjk/policyDocumentLibrary?q='
    + encodeURIComponent(keyword) + '&t=zhengcelibrary';
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 25000 });
    const allItems = [];
    for (let p = 0; p < maxPages; p++) {
      await page.waitForSelector('.dys_middle_result_content_item', { timeout: 20000 }).catch(() => {});
      await page.waitForTimeout(1500);
      const items = await page.evaluate(() => {
        return [...document.querySelectorAll('.dys_middle_result_content_item')].map(el => {
          const a = el.querySelector('a');
          const title = el.querySelector('.dysMiddleResultConItemTitle');
          const memo = el.querySelector('.dysMiddleResultConItemMemo');
          const rel = el.querySelectorAll('.dysMiddleResultConItemRelevant span');
          return {
            title: title ? title.textContent.trim() : '',
            source_url: a ? a.href : '',
            summary: memo ? memo.textContent.trim() : '',
            category: rel[0] ? rel[0].textContent.trim() : '',
            date: rel[1] ? rel[1].textContent.trim() : '',
          };
        });
      });
      allItems.push(...items);
      // 点击"下一页"（el-pagination），不可用则停止
      if (p < maxPages - 1) {
        const nextBtn = await page.$('.el-pagination .btn-next, .pagination .btn-next, li.next');
        if (!nextBtn) break;
        const disabled = await nextBtn.evaluate(el =>
          el.classList.contains('disabled') || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('is-disabled'));
        if (disabled) break;
        await nextBtn.click();
        await page.waitForTimeout(2000);
      }
    }
    // 去重（翻页可能重复）
    const seen = new Set();
    const uniq = allItems.filter(e => {
      if (seen.has(e.source_url)) return false;
      seen.add(e.source_url);
      return true;
    });
    console.log(JSON.stringify({ count: uniq.length, entries: uniq }));
  } catch (e) {
    console.log(JSON.stringify({ count: 0, entries: [], error: String(e).slice(0, 200) }));
  } finally {
    await browser.close();
  }
})();
