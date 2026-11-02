async (page) => {
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.reload({waitUntil:'networkidle'});
  await page.waitForTimeout(150);
  const first = await page.locator('[data-role="dynamic-title"]').evaluateAll(nodes => nodes.map(n => ({text:n.innerText, animations:n.getAnimations({subtree:true}).length})));
  await page.waitForTimeout(650);
  const dom = await page.evaluate(() => ({
    title: [...document.querySelectorAll('[data-role="dynamic-title"]')].map(n => ({text:n.innerText, animations:n.getAnimations({subtree:true}).length, visible:n.getBoundingClientRect().width > 0 && n.getBoundingClientRect().height > 0})),
    rows: [...document.querySelectorAll('tr[data-date]')].map(n => ({date:n.dataset.date, cells:[...n.querySelectorAll('td')].map(c=>c.innerText)})),
    cards: [...document.querySelectorAll('[data-stat]')].map(n => ({key:n.dataset.stat, text:n.innerText, background:getComputedStyle(n).backgroundColor, border:getComputedStyle(n).borderWidth, visible:n.getBoundingClientRect().width > 0 && n.getBoundingClientRect().height > 0})),
    body: document.body.innerText,
    overflow: document.documentElement.scrollWidth > window.innerWidth
  }));
  return {first, dom, errors, viewport:page.viewportSize()};
}
