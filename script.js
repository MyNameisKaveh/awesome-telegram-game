document.addEventListener('DOMContentLoaded', () => {
    const boardElement = document.getElementById('board');
    const statusArea = document.getElementById('status-area');
    const restartButton = document.getElementById('restart-button');
    const gameContainer = document.getElementById('game-container');

    const leaderboardButton = document.getElementById('leaderboard-button');
    const leaderboardSection = document.getElementById('leaderboard-section');
    const leaderboardListElement = document.getElementById('leaderboard-list');
    const closeLeaderboardButton = document.getElementById('close-leaderboard-button');
    
    const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

    const PLAYER_X = 'X';
    const PLAYER_O = 'O';
    let currentPlayer; // در startGame مقداردهی اولیه می‌شود
    let boardState;    // در startGame مقداردهی اولیه می‌شود
    let gameActive;    // در startGame مقداردهی اولیه می‌شود
    let cells = []; 

    const winningCombinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ];

    // ---------- شروع توابع بازی ----------

    function createBoardDOM() { // فقط DOM را می‌سازد یا به‌روز می‌کند
        boardElement.innerHTML = ''; 
        cells = []; 
        for (let i = 0; i < 9; i++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.index = i; // اندیس را به عنوان data attribute ذخیره می‌کنیم
            cell.addEventListener('click', handleCellClick);
            boardElement.appendChild(cell);
            cells.push(cell);
        }
    }

    function updateCellDOM(index, player) {
        if (cells[index]) {
            cells[index].textContent = player;
            if (player) {
                cells[index].classList.add(player.toLowerCase());
                cells[index].classList.add('occupied');
            } else { // برای پاک کردن سلول
                cells[index].classList.remove(PLAYER_X.toLowerCase(), PLAYER_O.toLowerCase(), 'occupied', 'winning-cell');
            }
        }
    }
    
    function updateStatusMessage(message) {
        statusArea.textContent = message;
    }

    function startGame() {
        currentPlayer = PLAYER_X;
        boardState = Array(9).fill(null);
        gameActive = true;
        gameContainer.classList.remove('game-over');
        
        cells.forEach((cell, index) => {
            updateCellDOM(index, null); // پاک کردن محتوای DOM سلول‌ها
        });
        
        updateStatusMessage(`نوبت بازیکن ${currentPlayer}`);
        if (leaderboardSection) hideLeaderboard();
    }

    function handleCellClick(event) {
        if (!gameActive) return;

        const clickedCell = event.target;
        const cellIndex = parseInt(clickedCell.dataset.index);

        if (isNaN(cellIndex) || boardState[cellIndex] !== null) {
            return;
        }

        boardState[cellIndex] = currentPlayer;
        updateCellDOM(cellIndex, currentPlayer);

        const winnerInfo = checkWin();
        if (winnerInfo.hasWinner) {
            endGame(false, winnerInfo.winningPlayer);
        } else if (boardState.every(cell => cell !== null)) {
            endGame(true, null); 
        } else {
            switchPlayer();
        }
    }

    function switchPlayer() {
        currentPlayer = currentPlayer === PLAYER_X ? PLAYER_O : PLAYER_X;
        updateStatusMessage(`نوبت بازیکن ${currentPlayer}`);
    }

    function checkWin() {
        for (const combination of winningCombinations) {
            const [a, b, c] = combination;
            if (boardState[a] && 
                boardState[a] === boardState[b] && 
                boardState[a] === boardState[c]) {
                // هایلایت کردن خانه‌های برنده
                combination.forEach(index => {
                    if (cells[index]) cells[index].classList.add('winning-cell');
                });
                return { hasWinner: true, winningPlayer: boardState[a], combination: combination }; 
            }
        }
        return { hasWinner: false, winningPlayer: null, combination: null }; 
    }

    async function submitScoreToAPI(score, gameType, telegramInitData) {
        const fullApiUrl = 'https://awesome-telegram-game.vercel.app/api/submit_score';
        let originalStatus = statusArea.textContent; // ذخیره پیام فعلی

        if (!telegramInitData) {
            console.warn("Telegram initData is not available. Score submission aborted.");
            updateStatusMessage(originalStatus + " (امتیاز ثبت نشد - نیاز به اجرای بازی از داخل تلگرام)");
            return;
        }
        console.log("Attempting to submit score:", { score, gameType, telegramInitDataAvailable: !!telegramInitData });
        updateStatusMessage(originalStatus + " (در حال ثبت امتیاز...)");

        try {
            const response = await fetch(fullApiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ score, game_type: gameType, telegramInitData }),
            });
            const result = await response.json();
            if (response.ok) {
                console.log("Score submitted successfully:", result);
                updateStatusMessage(originalStatus + ` (امتیاز شما: ${score} ثبت شد!)`);
            } else {
                console.error("Error submitting score - API error:", result);
                updateStatusMessage(originalStatus + ` (خطا در ثبت امتیاز: ${result.detail || 'خطای سرور'})`);
            }
        } catch (error) {
            console.error("Network or other error during score submission:", error);
            updateStatusMessage(originalStatus + " (خطای شبکه در ثبت امتیاز)");
        }
    }

    function endGame(isDraw, winner) { // winner هم به عنوان پارامتر اضافه شد
        gameActive = false;
        gameContainer.classList.add('game-over');

        let gameScore = 0; 
        let statusMessage = '';

        if (isDraw) {
            statusMessage = 'بازی مساوی شد! 😐';
            gameScore = 1; 
        } else {
            // winner همون currentPlayer هست که برنده شده
            statusMessage = `بازیکن ${winner} برنده شد! 🎉`; 
            if (winner === PLAYER_X) { // اگر X (فرضاً کاربر ما) برنده شد
                gameScore = 10; 
            } else { // اگر O برنده شد
                gameScore = 0; 
            }
        }
        
        updateStatusMessage(statusMessage);

        if (tg && tg.initData) {
            const initDataString = tg.initData;
            submitScoreToAPI(gameScore, "tictactoe_default_v1", initDataString);
        } else {
            console.warn("Telegram WebApp initData not available. Score will not be submitted.");
            updateStatusMessage(statusMessage + " (امتیاز در حالت تست ثبت نمی‌شود)");
        }
    }
    
    function applyTelegramTheme() { /* ... (کد این تابع بدون تغییر) ... */ }
    async function fetchLeaderboard() { /* ... (کد این تابع بدون تغییر) ... */ }
    function displayLeaderboard(leaderboardArray) { /* ... (کد این تابع بدون تغییر) ... */ }
    function showLeaderboard() { /* ... (کد این تابع بدون تغییر) ... */ }
    function hideLeaderboard() { /* ... (کد این تابع بدون تغییر) ... */ }
    
    // ---------- شروع اجرای اولیه و راه‌اندازی بازی ----------
    function initializeGame() {
        createBoardDOM(); // ساختن اولیه DOM برد
        startGame();      // مقداردهی اولیه وضعیت بازی و نمایش اولیه

        restartButton.addEventListener('click', startGame); // دکمه ریستارت، بازی جدید شروع می‌کند
        if (leaderboardButton) leaderboardButton.addEventListener('click', showLeaderboard);
        if (closeLeaderboardButton) closeLeaderboardButton.addEventListener('click', hideLeaderboard);

        if (tg) {
            tg.ready(); 
            applyTelegramTheme(); 
            tg.onEvent('themeChanged', applyTelegramTheme); 
            console.log("Telegram WebApp API initialized.");
            if (tg.initData) console.log("Raw initData:", tg.initData);
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                console.log("User data from initDataUnsafe:", tg.initDataUnsafe.user);
            }
        } else {
            console.warn("Telegram WebApp API not available. Running in standalone browser mode.");
        }
    }

    initializeGame(); // فراخوانی تابع اصلی برای راه‌اندازی همه چیز
});
