const puppeteer = require('/tmp/test_pup/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

(async () => {
    console.log('Launching headless Chrome...');
    const browser = await puppeteer.launch({
        executablePath: '/home/kennysk/.cache/puppeteer/chrome/linux-157.0.8103.50/chrome-linux64/chrome',
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-crash-reporter',
            '--no-zygote',
            '--single-process',
            '--window-size=1920,1080'
        ]
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    console.log('Navigating to http://127.0.0.1:8501 ...');
    await page.goto('http://127.0.0.1:8501', { waitUntil: 'networkidle2', timeout: 30000 });
    console.log('Page loaded successfully!');

    // Take a screenshot to verify UI is rendered
    await page.screenshot({ path: '/tmp/test_live_page.png' });
    console.log('Test live screenshot saved: /tmp/test_live_page.png');

    await browser.close();
})();
