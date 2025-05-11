document.addEventListener('DOMContentLoaded', () => {
    const boardElement = document.getElementById('board');
    const statusArea = document.getElementById('status-area');
    const restartButton = document.getElementById('restart-button');
    const gameContainer = document.getElementById('game-container');
    
    // دسترسی به API تلگرام وب‌اپ (اگر در محیط تلگرام باشد)
    const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

    // تنظیمات اولیه بازی
    const PLAYER_X = 'X';
    const PLAYER_O = 'O';
    let currentPlayer = PLAYER_X;
    let boardState = Array(9).fill(null); 
    let gameActive = true;
    let cells = []; 

    const winningCombinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], // ردیف‌ها
        [0, 3, 6], [1, 4, 7], [2, 5, 8], // ستون‌ها
        [0, 4, 8], [2, 4, 6]             // قطرها
    ];

    // ---------- شروع توابع بازی ----------

    function createBoard() {
        boardElement.innerHTML = ''; 
        cells = []; 
        for (let i = 0; i < 9; i++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.index = i;
            cell.addEventListener('click', handleCellClick);
            boardElement.appendChild(cell);
            cells.push(cell);
        }
    }

    function handleCellClick(event) {
        if (!gameActive) return;

        const clickedCell = event.target;
        const cellIndex = parseInt(clickedCell.dataset.index);

        if (boardState[cellIndex] !== null) {
            return;
        }

        boardState[cellIndex] = currentPlayer;
        clickedCell.textContent = currentPlayer;
        clickedCell.classList.add(currentPlayer.toLowerCase()); 
        clickedCell.classList.add('occupied');

        if (checkWin()) {
            endGame(false); 
        } else if (boardState.every(cell => cell !== null)) {
            endGame(true); 
        } else {
            switchPlayer();
        }
    }

    function switchPlayer() {
        currentPlayer = currentPlayer === PLAYER_X ? PLAYER_O : PLAYER_X;
        statusArea.textContent = `نوبت بازیکن ${currentPlayer}`;
    }

    function checkWin() {
        for (const combination of winningCombinations) {
            const [a, b, c] = combination;
            if (boardState[a] && boardState[a] === boardState[b] && boardState[a] === boardState[c]) {
                combination.forEach(index => cells[index].classList.add('winning-cell'));
                return true; 
            }
        }
        return false; 
    }

    async function submitScoreToAPI(score, gameType, telegramInitData) {
        const fullApiUrl = 'https://awesome-telegram-game.vercel.app/api/submit_score'; // URL کامل API شما

        console.log("Attempting to submit score:", { score, gameType, telegramInitData: telegramInitData ? 'Available' : 'Not Available' });

        if (!telegramInitData) {
            console.error("Telegram initData is not available. Score submission aborted.");
            statusArea.textContent += " (امتیاز ثبت نشد - نیاز به اجرای بازی از داخل تلگرام)";
            return; // اگر initData نباشد، امتیازی ارسال نمی‌شود
        }

        try {
            const response = await fetch(fullApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    score: score,
                    game_type: gameType,
                    telegramInitData: telegramInitData 
                }),
            });

            const result = await response.json(); // همیشه سعی کن پاسخ را به عنوان JSON بخوانی

            if (response.ok) { // status code 200-299
                console.log("Score submitted successfully:", result);
                statusArea.textContent += ` (امتیاز شما: ${score} ثبت شد! وضعیت: ${result.message || 'موفق'})`;
            } else { // status code 4xx or 5xx
                console.error("Error submitting score - API responded with an error:", result);
                statusArea.textContent += ` (خطا در ثبت امتیاز: ${result.detail || response.statusText || 'خطای سرور'})`;
            }
        } catch (error) { // خطای شبکه یا خطای دیگر در fetch
            console.error("Network or other error during score submission:", error);
            statusArea.textContent += " (خطا در شبکه هنگام ثبت امتیاز یا پاسخ نامعتبر از سرور)";
        }
    }

    function endGame(isDraw) {
        gameActive = false;
        gameContainer.classList.add('game-over');

        let gameScore = 0; 
        let statusMessage = '';

        if (isDraw) {
            statusMessage = 'بازی مساوی شد! 😐';
            gameScore = 1; 
        } else {
            statusMessage = `بازیکن ${currentPlayer} برنده شد! 🎉`;
            if (currentPlayer === PLAYER_X) { 
                gameScore = 10; 
            } else { 
                gameScore = 0; 
            }
        }
        
        statusArea.textContent = statusMessage; // اول پیام نتیجه بازی نمایش داده شود

        // تلاش برای ارسال امتیاز به API
        if (tg && tg.initData) { // چک می‌کنیم که tg و initData معتبر باشند
            const initDataString = tg.initData;
            console.log("initData found, proceeding to submit score.");
            submitScoreToAPI(gameScore, "tictactoe_default_v1", initDataString);
        } else {
            console.warn("Telegram WebApp initData not available or tg object is null. Score will not be submitted.");
            statusArea.textContent += " (بازی در محیط تست، امتیاز ثبت نمی‌شود)";
        }
    }

    function restartGame() {
        currentPlayer = PLAYER_X;
        boardState = Array(9).fill(null);
        gameActive = true;
        gameContainer.classList.remove('game-over');
        
        cells.forEach(cell => {
            cell.textContent = '';
            cell.classList.remove('x', 'o', 'occupied', 'winning-cell');
        });
        // پیام اولیه بعد از ریستارت باید توسط createBoard یا اینجا تنظیم شود
        statusArea.textContent = `نوبت بازیکن ${currentPlayer}`; 
    }
    
    function applyTelegramTheme() {
        if (tg && tg.themeParams) {
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
    
    if (tg) { // اگر در محیط تلگرام هستیم
        tg.ready(); // به تلگرام اطلاع می‌دهد که وب‌اپ آماده است
        applyTelegramTheme(); // اعمال تم اولیه
        tg.onEvent('themeChanged', applyTelegramTheme); // گوش دادن به تغییرات تم
        // tg.expand(); // اگر می‌خواهید وب‌اپ تمام صفحه شود
        console.log("Telegram WebApp API initialized.");
        console.log("initData (raw):", tg.initData); // لاگ کردن initData برای دیباگ
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            console.log("User data from initDataUnsafe:", tg.initDataUnsafe.user);
        }
    } else {
        console.warn("Telegram WebApp API not available. Running in standalone browser mode.");
    }
    
    // ساختن صفحه بازی اولیه و تنظیم پیام اولیه
    createBoard();
    statusArea.textContent = `نوبت بازیکن ${currentPlayer}`;

    // اضافه کردن Event Listener به دکمه شروع مجدد
    restartButton.addEventListener('click', restartGame);

});
