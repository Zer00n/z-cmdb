const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  const imgDir = path.resolve(__dirname, '../img');

  // 1. Login page (English)
  await page.goto('http://localhost:5174/login', { waitUntil: 'networkidle2', timeout: 15000 });
  await page.waitForSelector('.login-page', { timeout: 5000 });
  await new Promise(r => setTimeout(r, 500));
  await page.screenshot({ path: path.join(imgDir, 'i18n-login-en.png'), fullPage: false });
  console.log('Screenshot: login page (EN)');

  // 2. Login
  await page.type('input[autocomplete="username"]', 'admin');
  await page.type('input[autocomplete="current-password"]', 'syler052802ALEX!@#');
  await page.click('.login-btn');
  await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 1500));

  // 3. Dashboard (English)
  await page.screenshot({ path: path.join(imgDir, 'i18n-dashboard-en.png'), fullPage: false });
  console.log('Screenshot: dashboard (EN)');

  // 4. Click language toggle to switch to Chinese
  const langBtn = await page.$('.lang-toggle');
  if (langBtn) {
    await langBtn.click();
    await new Promise(r => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(imgDir, 'i18n-dashboard-zh.png'), fullPage: false });
    console.log('Screenshot: dashboard (ZH)');
  } else {
    console.log('Language toggle button not found');
  }

  // 5. Settings page (Chinese)
  await page.goto('http://localhost:5174/settings', { waitUntil: 'networkidle2', timeout: 10000 });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(imgDir, 'i18n-settings-zh.png'), fullPage: false });
  console.log('Screenshot: settings (ZH)');

  // 6. Settings page in English - switch via lang toggle
  const langToggle2 = await page.$('.lang-toggle');
  if (langToggle2) {
    await langToggle2.click();
    await new Promise(r => setTimeout(r, 1000));
  }
  await page.screenshot({ path: path.join(imgDir, 'i18n-settings-en.png'), fullPage: false });
  console.log('Screenshot: settings (EN)');

  // 7. Combined preview - dashboard EN
  await page.goto('http://localhost:5174/dashboard', { waitUntil: 'networkidle2', timeout: 10000 });
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: path.join(imgDir, 'i18n-preview.png'), fullPage: false });
  console.log('Screenshot: i18n-preview.png updated');

  await browser.close();
  console.log('All screenshots done!');
})();
