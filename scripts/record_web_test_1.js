/**
 * Script: scripts/record_web_test_1.js
 * Ghi hình tự động tương tác thực tế từ trình duyệt Chrome (1080p @ 30 FPS):
 * 1. Trang phản ánh sinh viên: Điền thông tin và gửi phản ánh học vụ -> Nhận thông báo biên nhận thành công.
 * 2. Chuyển qua trong tiếp nhận (Bàn duyệt cán bộ): Xem thông tin AI đã tự động xử lý
 *    (Phân loại chuyên môn, trích xuất quy chế PROC_TC_01, SLA 24-48h, xem email đã giải quyết).
 * 3. Hoàn toàn KHÔNG dùng tính năng bánh răng ("răng cưa").
 */

const puppeteer = require('/tmp/test_pup/node_modules/puppeteer');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const OUTPUT_VIDEO = path.resolve(__dirname, '../output/web_test_live_demo.mp4');
const FPS = 30;
const FRAME_INTERVAL = Math.floor(1000 / FPS);

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
    console.log('=== QUAY VIDEO DEMO: TẠO PHẢN ÁNH -> CHUYỂN QUA TIẾP NHẬN XEM ĐÃ XỬ LÝ ===');

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
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

    // 1. Mở trang phản ánh sinh viên
    console.log('-> Đang mở Trang phản ánh sinh viên (http://127.0.0.1:8501/?view=student)...');
    await page.goto('http://127.0.0.1:8501/?view=student', { waitUntil: 'networkidle2', timeout: 30000 });
    await sleep(1200);

    // Setup virtual cursor
    async function setupCursor() {
        await page.evaluate(() => {
            let cursor = document.getElementById('virtual-cursor');
            if (!cursor) {
                cursor = document.createElement('div');
                cursor.id = 'virtual-cursor';
                cursor.style.position = 'fixed';
                cursor.style.width = '20px';
                cursor.style.height = '20px';
                cursor.style.borderRadius = '50%';
                cursor.style.backgroundColor = 'rgba(37, 99, 235, 0.9)';
                cursor.style.border = '2px solid #ffffff';
                cursor.style.boxShadow = '0 0 12px rgba(37, 99, 235, 0.9)';
                cursor.style.pointerEvents = 'none';
                cursor.style.zIndex = '9999999';
                cursor.style.left = '960px';
                cursor.style.top = '300px';
                cursor.style.transform = 'translate(-50%, -50%)';
                cursor.style.transition = 'transform 0.12s ease, background-color 0.12s ease';
                document.body.appendChild(cursor);
            }

            window.triggerClickEffect = (x, y) => {
                const ripple = document.createElement('div');
                ripple.style.position = 'fixed';
                ripple.style.left = `${x}px`;
                ripple.style.top = `${y}px`;
                ripple.style.width = '10px';
                ripple.style.height = '10px';
                ripple.style.borderRadius = '50%';
                ripple.style.border = '2px solid #ef4444';
                ripple.style.transform = 'translate(-50%, -50%) scale(1)';
                ripple.style.opacity = '1';
                ripple.style.pointerEvents = 'none';
                ripple.style.zIndex = '9999998';
                ripple.style.transition = 'all 0.4s ease-out';
                document.body.appendChild(ripple);

                cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.95)';
                cursor.style.transform = 'translate(-50%, -50%) scale(0.75)';

                setTimeout(() => {
                    ripple.style.width = '45px';
                    ripple.style.height = '45px';
                    ripple.style.opacity = '0';
                }, 20);

                setTimeout(() => {
                    cursor.style.backgroundColor = 'rgba(37, 99, 235, 0.9)';
                    cursor.style.transform = 'translate(-50%, -50%) scale(1)';
                    ripple.remove();
                }, 250);
            };

            window.setCursorPos = (x, y) => {
                cursor.style.left = `${x}px`;
                cursor.style.top = `${y}px`;
            };
        });
    }

    await setupCursor();

    // 2. Khởi động ghi hình FFmpeg
    console.log(`-> Bắt đầu quay video FFmpeg to: ${OUTPUT_VIDEO}...`);
    const ffmpeg = spawn('ffmpeg', [
        '-y',
        '-f', 'image2pipe',
        '-vcodec', 'mjpeg',
        '-r', String(FPS),
        '-i', '-',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        OUTPUT_VIDEO
    ]);

    let isRecording = true;
    let frameCount = 0;

    const recordingLoop = (async () => {
        while (isRecording) {
            const t0 = Date.now();
            try {
                const buffer = await page.screenshot({ type: 'jpeg', quality: 85 });
                if (ffmpeg.stdin.writable) {
                    ffmpeg.stdin.write(buffer);
                    frameCount++;
                }
            } catch (err) {}
            const elapsed = Date.now() - t0;
            const waitTime = Math.max(5, FRAME_INTERVAL - elapsed);
            await sleep(waitTime);
        }
    })();

    let currentMouse = { x: 960, y: 300 };
    async function moveMouseSmooth(targetX, targetY, durationMs = 500) {
        const steps = Math.max(8, Math.floor(durationMs / 30));
        const startX = currentMouse.x;
        const startY = currentMouse.y;
        for (let i = 1; i <= steps; i++) {
            const prog = i / steps;
            const ease = prog < 0.5 ? 2 * prog * prog : -1 + (4 - 2 * prog) * prog;
            const nx = Math.round(startX + (targetX - startX) * ease);
            const ny = Math.round(startY + (targetY - startY) * ease);
            await page.evaluate((x, y) => window.setCursorPos(x, y), nx, ny);
            await sleep(30);
        }
        currentMouse = { x: targetX, y: targetY };
    }

    async function clickCurrentMouse() {
        await page.evaluate((x, y) => window.triggerClickEffect(x, y), currentMouse.x, currentMouse.y);
        await sleep(150);
    }

    // ==================== BƯỚC 1: TẠO 1 PHẢN ÁNH Ở TRANG PHẢN ÁNH ====================
    console.log('-> Bước 1: Sinh viên điền thông tin và phản ánh học vụ...');
    await sleep(600);

    // Di chuyển tới ô Họ tên
    await moveMouseSmooth(250, 310, 500);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const input = document.querySelector('input[aria-label="Họ và tên sinh viên *"]');
        if (input) {
            input.value = 'Nguyễn Văn A';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    await sleep(500);

    // Ô Mã sinh viên
    await moveMouseSmooth(430, 310, 400);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const input = document.querySelector('input[aria-label="Mã sinh viên *"]');
        if (input) {
            input.value = '20233780';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    await sleep(400);

    // Ô Số điện thoại
    await moveMouseSmooth(250, 385, 400);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const input = document.querySelector('input[aria-label="Số điện thoại liên hệ *"]');
        if (input) {
            input.value = '0987654321';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    await sleep(400);

    // Ô Email
    await moveMouseSmooth(430, 385, 400);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const input = document.querySelector('input[aria-label="Email nhận kết quả *"]');
        if (input) {
            input.value = '20233780@eaut.edu.vn';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    await sleep(400);

    // Chọn Nhóm dịch vụ: Học bổng, chế độ và chính sách
    await moveMouseSmooth(320, 460, 500);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const sel = document.querySelector('input[aria-label="Nhóm dịch vụ cần hỗ trợ *"]');
        if (sel) {
            sel.click();
        }
    });
    await sleep(300);
    // Chọn mục thứ 4 (Học bổng, chế độ và chính sách)
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await sleep(400);

    // Ô Tóm tắt vấn đề
    await moveMouseSmooth(320, 535, 400);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const input = document.querySelector('input[aria-label="Tóm tắt vấn đề *"]');
        if (input) {
            input.value = 'Đề nghị đối soát học phí đã chuyển khoản qua ngân hàng';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    await sleep(500);

    // Ô Mô tả chi tiết nội dung
    await moveMouseSmooth(320, 640, 400);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const textarea = document.querySelector('textarea[aria-label="Mô tả chi tiết nội dung"]');
        if (textarea) {
            textarea.value = "Kính gửi Phòng Tài chính - Kế toán và Phòng Quản lý Đào tạo trường ĐH Công nghệ Đông Á. Em là sinh viên khóa K14, MSSV: 20233780, email: 20233780@eaut.edu.vn. Em đã chuyển khoản nộp học phí học kỳ I năm học 2024 - 2025 vào tài khoản ngân hàng chính thức của Nhà trường ngày 12/11/2024, nội dung chuyển khoản đúng cú pháp: '20233780 Nguyen Van A nop hoc phi HK1'. Tuy nhiên, hiện tại trên cổng thông tin sinh viên daotao.eaut.edu.vn trạng thái tài chính của em vẫn chưa được gạch nợ. Kính mong Quý Phòng kiểm tra, đối soát giao dịch ngân hàng và cập nhật trạng thái học phí trên hệ thống giúp em.";
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    await sleep(800);

    // Di chuyển tới nút Gửi phiếu hỗ trợ
    console.log('-> Bước 1: Nhấn [Gửi phiếu hỗ trợ]...');
    await moveMouseSmooth(300, 840, 600);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const submitBtn = buttons.find(b => b.innerText && b.innerText.includes('Gửi phiếu hỗ trợ'));
        if (submitBtn) submitBtn.click();
    });
    await sleep(2500); // Đợi hệ thống phản hồi kết quả và hiển thị banner

    // ==================== BƯỚC 2: CHUYỂN QUA TRONG TIẾP NHẬN XEM ĐÃ XỬ LÝ ====================
    console.log('-> Bước 2: Chuyển qua Trong tiếp nhận (Bàn duyệt cán bộ)...');
    await page.goto('http://127.0.0.1:8501/?view=workbench', { waitUntil: 'networkidle2' });
    await sleep(1000);
    await setupCursor();

    // Di chuyển chuột tới tiêu đề Bàn duyệt cán bộ
    await moveMouseSmooth(450, 70, 600);
    await sleep(600);

    // Chuyển bộ lọc qua "Phản ánh đã gửi" để xem hồ sơ đã được xử lý hoàn tất
    console.log('-> Bước 2: Chọn mục [Phản ánh đã gửi]...');
    await moveMouseSmooth(330, 248, 500);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const labels = Array.from(document.querySelectorAll('label'));
        const sentRadio = labels.find(l => l.innerText && l.innerText.includes('Phản ánh đã gửi'));
        if (sentRadio) {
            const input = sentRadio.querySelector('input') || sentRadio;
            input.click();
        }
    });
    await sleep(1000);

    // Chọn phiếu vừa được xử lý trên bảng hàng đợi bên trái
    console.log('-> Bước 2: Nhấp chọn phiếu học phí vừa được tiếp nhận...');
    await moveMouseSmooth(260, 480, 600);
    await clickCurrentMouse();
    await sleep(800);

    // Xem thông tin AI đã xử lý bên phải:
    console.log('-> Bước 2: Xem thông tin AI đã xử lý (Thẻ hồ sơ, Căn cứ quy chế, SLA)...');
    // 1. Thẻ hồ sơ học vụ & Badge AI Tin cậy
    await moveMouseSmooth(680, 195, 600);
    await sleep(800);

    // 2. Nội dung phản ánh từ Sinh viên
    await moveMouseSmooth(650, 340, 600);
    await sleep(800);

    // 3. Căn cứ quy chế chính thức EAUT & SLA đối soát ngân hàng
    await moveMouseSmooth(650, 520, 600);
    await sleep(1000);

    // 4. Mở accordion "Nội dung email đã gửi" để xem văn bản chính thức
    console.log('-> Bước 2: Mở xem toàn bộ văn bản email giải quyết chính thức...');
    await moveMouseSmooth(520, 675, 600);
    await clickCurrentMouse();
    await page.evaluate(() => {
        const details = Array.from(document.querySelectorAll('details, [data-testid="stExpander"]'));
        const mailExpander = details.find(d => d.innerText && d.innerText.includes('Nội dung email đã gửi'));
        if (mailExpander) {
            const summary = mailExpander.querySelector('summary');
            if (summary) summary.click();
            else mailExpander.click();
        }
    });
    await sleep(1000);

    // Cuộn nhẹ xem chi tiết email
    await moveMouseSmooth(650, 750, 500);
    await page.evaluate(() => {
        window.scrollBy({ top: 350, behavior: 'smooth' });
    });
    await sleep(2200);

    // Kết thúc ghi hình
    console.log('-> Kết thúc quá trình ghi hình video demo...');
    isRecording = false;
    await recordingLoop;

    ffmpeg.stdin.end();
    await new Promise(resolve => ffmpeg.on('close', resolve));
    await browser.close();

    console.log(`\n🎉 HOÀN TẤT QUAY DEMO CHUẨN: ${OUTPUT_VIDEO}`);
    console.log(`-> Tổng khung hình: ${frameCount} frames (~${(frameCount / FPS).toFixed(1)}s, 1080p).`);
}

main().catch(err => {
    console.error('Error recording demo:', err);
    process.exit(1);
});
