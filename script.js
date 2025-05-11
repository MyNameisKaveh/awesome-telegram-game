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
    let currentPlayer = PLAYER_X;
    let boardState = Array(9).fill(null); 
    let gameActive = true;
    let cells = []; 

    const winningCombinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ];

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
            if (boardState[a] && boardState[a] === boardState[b] && board_state[a] === boardState[c]) { // اصلاح board_state به boardState
                combination.forEach(index => cells[index].classList.add('winning-cell'));
                return true; 
            }
        }
        return false; 
    }

    async function submitScoreToAPI(score, gameType, telegramInitData) {
        const fullApiUrl = 'https://awesome-telegram-game.vercel.app/api/submit_score';

        console.log("Attempting to submit score:", { score, gameType, telegramInitData: telegramInitData ? 'Available' : 'Not Available' });

        if (!telegramInitData) {
            console.error("Telegram initData is not available. Score submission aborted.");
            statusArea.textContent += " (امتیاز ثبت نشد - نیاز به اجرای بازی از داخل تلگرام)";
            return;
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

            const result = await response.json(); 

            if (response.ok) {
                console.log("Score submitted successfully:", result);
                statusArea.textContent += ` (امتیاز شما: ${score} ثبت شد! ${result.message || ''})`;
            } else {
                console.error("Error submitting score - API responded with an error:", result);
                statusArea.textContent += ` (خطا در ثبت امتیاز: ${result.detail || response.statusText || 'خطای سرور'})`;
            }
        } catch (error) {
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
        
        statusArea.textContent = statusMessage;

        if (tg && tg.initData) {
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
        statusArea.textContent = `نوبت بازیکن ${currentPlayer}`; 
        hideLeaderboard(); // بستن لیدربورد هنگام شروع مجدد بازی
    }
    
    function applyTelegramTheme() {
        if (tg && tg.themeParams) {
            document.documentElement.style.setProperty('--telegram-bg-color', tg.themeParams.bg_color || '#ffffff');
            document.documentElement.style.setProperty('--telegram-text-color', tg.themeParams.text_color || '#000000');
            // ... بقیه متغیرهای تم ...
            document.documentElement.style.setProperty('--telegram-hint-color', tg.themeParams.hint_color || '#999999');
            document.documentElement.style.setProperty('--telegram-link-color', tg.themeParams.link_color || '#2481cc');
            document.documentElement.style.setProperty('--telegram-button-color', tg.themeParams.button_color || '#2481cc');
            document.documentElement.style.setProperty('--telegram-button-text-color', tg.themeParams.button_text_color || '#ffffff');
            document.documentElement.style.setProperty('--telegram-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f4f4f4');
        }
    }

    async function fetchLeaderboard() {
        const gameType = "tictactoe_default_v1";
        const limit = 10;
        const leaderboardApiUrl = `https://awesome-telegram-game.vercel.app/api/leaderboard?game_type=${gameType}&limit=${limit}`;
        
        console.log("Fetching leaderboard from:", leaderboardApiUrl);
        leaderboardListElement.innerHTML = '<p>در حال بارگذاری لیدربورد...</p>';

        try {
            const response = await fetch(leaderboardApiUrl);
            const data = await response.json();

            if (response.ok) {
                console.log("Leaderboard data fetched:", data);
                displayLeaderboard(data.leaderboard);
            } else {
                console.error("Error fetching leaderboard:", data);
                leaderboardListElement.innerHTML = `<p>خطا در دریافت لیدربورد: ${data.detail || response.statusText}</p>`;
            }
        } catch (error) {
            console.error("Network or other error fetching leaderboard:", error);
            leaderboardListElement.innerHTML = "<p>خطای شبکه یا سرور هنگام دریافت لیدربورد.</p>";
        }
    }

    function displayLeaderboard(leaderboardArray) {
        if (!leaderboardArray || leaderboardArray.length === 0) {
            leaderboardListElement.innerHTML = "<p>هنوز هیچ رکوردی در لیدربورد ثبت نشده است.</p>";
            return;
        }

        const ol = document.createElement('ol');
        leaderboardArray.forEach((player, index) => {
            const li = document.createElement('li');
            const rankSpan = document.createElement('span');
            rankSpan.classList.add('player-rank');
            rankSpan.textContent = `${index + 1}.`;
            const nameSpan = document.createElement('span');
            nameSpan.classList.add('player-name');
            nameSpan.textContent = player.name || `User ${player.user_id.substring(0,6)}`;
            const scoreSpan = document.createElement('span');
            scoreSpan.classList.add('player-score');
            scoreSpan.textContent = player.score;
            li.appendChild(rankSpan);
            li.appendChild(nameSpan);
            li.appendChild(scoreSpan);
            ol.appendChild(li);
        });

        leaderboardListElement.innerHTML = '';
        leaderboardListElement.appendChild(ol);
    }

    function showLeaderboard() {
        leaderboardSection.classList.remove('hidden');
        fetchLeaderboard(); 
    }

    function hideLeaderboard() {
        leaderboardSection.classList.add('hidden');
    }
    
    // ---------- شروع اجرای اولیه بازی ----------
    if (tg) {
        tg.ready(); 
        applyTelegramTheme(); 
        tg.onEvent('themeChanged', applyTelegramTheme); 
        console.log("Telegram WebApp API initialized.");
        if (tg.initData) console.log("initData (raw):", tg.initData);
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            console.log("User data from initDataUnsafe:", tg.initDataUnsafe.user);
        }
    } else {
        console.warn("Telegram WebApp API not available. Running in standalone browser mode.");
    }
    
    createBoard();
    statusArea.textContent = `نوبت بازیکن ${currentPlayer}`;

    restartButton.addEventListener('click', restartGame);
    if (leaderboardButton) leaderboardButton.addEventListener('click', showLeaderboard);
    if (closeLeaderboardButton) closeLeaderboardButton.addEventListener('click', hideLeaderboard);
});
