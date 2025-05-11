document.addEventListener('DOMContentLoaded', () => {
    const boardElement = document.getElementById('board');
    const statusArea = document.getElementById('status-area');
    const restartButton = document.getElementById('restart-button');
    const gameContainer = document.getElementById('game-container');
    
    // دسترسی به API تلگرام وب‌اپ
    const tg = window.Telegram.WebApp;

    // تنظیمات اولیه بازی
    const PLAYER_X = 'X';
    const PLAYER_O = 'O';
    let currentPlayer = PLAYER_X;
    let boardState = Array(9).fill(null); // null: خالی, 'X', 'O'
    let gameActive = true;
    let cells = []; // آرایه‌ای برای نگهداری عناصر DOM خانه‌ها

    // ترکیب‌های برنده شدن
    const winningCombinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], // ردیف‌ها
        [0, 3, 6], [1, 4, 7], [2, 5, 8], // ستون‌ها
        [0, 4, 8], [2, 4, 6]             // قطرها
    ];

    // ---------- شروع توابع بازی ----------

    // تابع برای ساختن خانه‌های بازی
    function createBoard() {
        boardElement.innerHTML = ''; // پاک کردن صفحه قبلی اگر وجود دارد
        cells = []; // خالی کردن آرایه خانه‌ها
        for (let i = 0; i < 9; i++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.index = i;
            cell.addEventListener('click', handleCellClick);
            boardElement.appendChild(cell);
            cells.push(cell);
        }
    }

    // تابع برای مدیریت کلیک روی یک خانه
    function handleCellClick(event) {
        if (!gameActive) return;

        const clickedCell = event.target;
        const cellIndex = parseInt(clickedCell.dataset.index);

        if (boardState[cellIndex] !== null) { // اگر خانه پر بود
            return;
        }

        // اعمال حرکت
        boardState[cellIndex] = currentPlayer;
        clickedCell.textContent = currentPlayer;
        clickedCell.classList.add(currentPlayer.toLowerCase()); // برای استایل x یا o
        clickedCell.classList.add('occupied');

        // بررسی نتیجه
        if (checkWin()) {
            endGame(false); // false یعنی مساوی نشده، کسی برده
        } else if (boardState.every(cell => cell !== null)) { // همه خانه‌ها پر شده
            endGame(true); // true یعنی مساوی شده
        } else {
            switchPlayer();
        }
    }

    // تابع برای تغییر نوبت بازیکن
    function switchPlayer() {
        currentPlayer = currentPlayer === PLAYER_X ? PLAYER_O : PLAYER_X;
        statusArea.textContent = `نوبت بازیکن ${currentPlayer}`;
    }

    // تابع برای بررسی برنده شدن
    function checkWin() {
        for (const combination of winningCombinations) {
            const [a, b, c] = combination;
            if (boardState[a] && boardState[a] === boardState[b] && boardState[a] === boardState[c]) {
                // هایلایت کردن خانه‌های برنده
                combination.forEach(index => cells[index].classList.add('winning-cell'));
                return true; // یک نفر برنده شده
            }
        }
        return false; // هیچکس هنوز نبرده
    }

    // تابع برای پایان بازی
    function endGame(isDraw) {
        gameActive = false;
        gameContainer.classList.add('game-over'); // اضافه کردن کلاس برای استایل‌های خاص پایان بازی

        if (isDraw) {
            statusArea.textContent = 'بازی مساوی شد! 😐';
        } else {
            statusArea.textContent = `بازیکن ${currentPlayer} برنده شد! 🎉`;
        }
        
        // (اختیاری) ارسال داده به بات در آینده
        // if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        //     const resultData = {
        //         winner: isDraw ? null : currentPlayer,
        //         isDraw: isDraw,
        //         userId: tg.initDataUnsafe.user.id
        //     };
        //     tg.sendData(JSON.stringify(resultData));
        // }
    }

    // تابع برای شروع مجدد بازی
    function restartGame() {
        currentPlayer = PLAYER_X;
        boardState = Array(9).fill(null);
        gameActive = true;
        gameContainer.classList.remove('game-over');
        statusArea.textContent = `نوبت بازیکن ${currentPlayer}`;
        
        cells.forEach(cell => {
            cell.textContent = '';
            cell.classList.remove('x', 'o', 'occupied', 'winning-cell');
        });

        // (اختیاری) اگر از تلگرام باز شده، شاید بخواهید رنگ‌های تم رو مجدد اعمال کنید
        // applyTelegramTheme();
    }
    
    // تابع برای اعمال رنگ‌های تم تلگرام (اگر نیاز باشد)
    function applyTelegramTheme() {
        if (tg.themeParams) {
            document.documentElement.style.setProperty('--telegram-bg-color', tg.themeParams.bg_color || '#ffffff');
            document.documentElement.style.setProperty('--telegram-text-color', tg.themeParams.text_color || '#000000');
            document.documentElement.style.setProperty('--telegram-hint-color', tg.themeParams.hint_color || '#999999');
            document.documentElement.style.setProperty('--telegram-link-color', tg.themeParams.link_color || '#2481cc');
            document.documentElement.style.setProperty('--telegram-button-color', tg.themeParams.button_color || '#2481cc');
            document.documentElement.style.setProperty('--telegram-button-text-color', tg.themeParams.button_text_color || '#ffffff');
            document.documentElement.style.setProperty('--telegram-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f4f4f4');
        }
    }

    // ---------- شروع اجرای اولیه بازی ----------
    
    // وقتی وب‌اپ تلگرام آماده است
    tg.ready(); // به تلگرام اطلاع می‌دهد که وب‌اپ آماده است
    
    // (اختیاری) هماهنگی با دکمه اصلی تلگرام (MainButton)
    // tg.MainButton.setText("بستن بازی");
    // tg.MainButton.onClick(() => tg.close());
    // tg.MainButton.show();

    // (اختیاری) درخواست تغییر اندازه پنجره وب‌اپ
    // tg.expand();

    // اعمال تم تلگرام در ابتدا
    applyTelegramTheme();
    // و همچنین هر بار که تم تغییر می‌کند (اگر از طریق ایونت پشتیبانی شود)
    tg.onEvent('themeChanged', applyTelegramTheme);


    // ساختن صفحه بازی اولیه
    createBoard();
    statusArea.textContent = `نوبت بازیکن ${currentPlayer}`; // تنظیم پیام اولیه

    // اضافه کردن Event Listener به دکمه شروع مجدد
    restartButton.addEventListener('click', restartGame);

});
