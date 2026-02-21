const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('http://localhost:5173/test-dashboard-page');
  await page.waitForTimeout(5000);
  
  // Click Risks tab
  const tabs = await page.locator('button:has-text("Risks")').first();
  await tabs.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/risks-tab.png' });
  
  // Click Schools tab
  const schoolsTab = await page.locator('button:has-text("Schools")').first();
  await schoolsTab.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/schools-tab.png' });
  
  // Click POIs tab
  const poisTab = await page.locator('button:has-text("POIs")').first();
  await poisTab.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/pois-tab.png', fullPage: true });
  
  // Click Greenspace tab
  const greenTab = await page.locator('button:has-text("Greenspace")').first();
  await greenTab.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/greenspace-tab.png', fullPage: true });
  
  // Click Demographics tab
  const demoTab = await page.locator('button:has-text("Demographics")').first();
  await demoTab.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/demographics-tab.png', fullPage: true });

  await browser.close();
})();
