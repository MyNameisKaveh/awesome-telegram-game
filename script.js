document.addEventListener('DOMContentLoaded', () => {
    // عناصر DOM اصلی
    const appContainer = document.getElementById('app-container');
    const gameModeSelectionSection = document.getElementById('game-mode-selection');
    const gameBoardSection = document.getElementById('game-board-section');
    const leaderboardSection = document.getElementById('leaderboard-section');

    // عناصر بخش انتخاب حالت
    const playAiButton = document.getElementById('play-ai-button');
    const createOnlineGameButton = document.getElementById('create-online-game-button');
    const joinGameIdInput = document.getElementById('join-game-id-input');
    const joinOnlineGameButton = document.getElementById('join-online-game-button');
    const showLeaderboardFromMenuButton = document.getElementById('show-leaderboard-from-menu-button');

    // عناصر بخش بازی
    const gameTitleElement = document.getElementById('game-title');
    const statusArea = document.getElementById('status-area');
    const gameInfoArea = document.getElementById('game-info-area'); // برای کد بازی آنلاین و غیره
    const boardElement = document.getElementById('board');
    const restartButton = document.getElementById('restart-button'); // ممکن است به "خروج" تغییر کاربرد دهد

    // عناصر بخش لیدربورد
    const leaderboardListElement = document.getElementById('leaderboard-list');
    const closeLeaderboardButton = document.getElementById('close-leaderboard-button');
    
    const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

    // وضعیت‌های بازی
    const PLAYER_X = 'X';
    const PLAYER_O = 'O';
    let मानवPlayerSymbol = PLAYER_X; // بازیکن انسانی همیشه X است (فعلاً)
    let aiPlayerSymbol = PLAYER_O;
    
    let currentPlayer; 
    let boardState;    
    let gameActive;    
    let cells = []; 

    let currentGamemode = null; // 'ai', 'online_pvp_host', 'online_pvp_guest'
    let onlineGameId = null;
    let onlineGamePollingInterval = null;

    const winningCombinations = [ /* ... (بدون تغییر) ... */ ];

    // ---------- توابع مدیریت UI ----------
    function showSection(sectionElement) {
        gameModeSelectionSection.classList.add('hidden');
        gameBoardSection.classList.add('hidden');
        leaderboardSection.classList.add('hidden');
        if (sectionElement) {
            sectionElement.classList.remove('hidden');
        }
    }

    // ---------- توابع بازی اصلی ----------
    function createBoardDOM() { /* ... (بدون تغییر از نسخه قبلی که فقط DOM می‌ساخت) ... */ }
    function updateCellDOM(index, player) { /* ... (بدون تغییر) ... */ }
    function updateStatusMessage(message) { statusArea.textContent = message; }
    function updateGameInfoMessage(message) { gameInfoArea.textContent = message; }

    function initializeNewGame(mode) {
        currentGamemode = mode;
        currentPlayer = PLAYER_X; // بازیکن انسانی معمولاً X و اول شروع می‌کند
        boardState = Array(9).fill(null);
        gameActive = true;
        gameContainer.classList.remove('game-over'); // از game-board-section استفاده شود
        
        if(gameBoardSection) gameBoardSection.classList.remove('game-over'); // اصلاح شده


        cells.forEach((cell, index) => updateCellDOM(index, null));
        
        if (mode === 'ai') {
            if(gameTitleElement) gameTitleElement.textContent = "بازی با کامپیوتر";
            updateStatusMessage(`شما (X) مقابل کامپیوتر (O). نوبت شما.`);
            updateGameInfoMessage(""); // اطلاعات اضافی برای بازی AI لازم نیست
        } else if (mode === 'online_pvp_host' || mode === 'online_pvp_guest') {
            if(gameTitleElement) gameTitleElement.textContent = "بازی آنلاین";
            // پیام وضعیت و اطلاعات بازی آنلاین توسط توابع دیگر مدیریت می‌شود
        }
        showSection(gameBoardSection);
    }

    function handleCellClick(event) {
        if (!gameActive || (currentGamemode === 'online_pvp_host' && currentPlayer !== मानवPlayerSymbol && onlineGameId) || (currentGamemode === 'online_pvp_guest' && currentPlayer !== मानवPlayerSymbol && onlineGameId) ) {
             // اگر بازی فعال نیست یا نوبت بازیکن آنلاین انسانی نیست، کاری نکن
            if (currentGamemode && currentGamemode.startsWith('online_pvp') && currentPlayer !== मानवPlayerSymbol) {
                console.log("Not your turn in online game.");
            }
            return;
        }


        const clickedCell = event.target;
        const cellIndex = parseInt(clickedCell.dataset.index);

        if (isNaN(cellIndex) || boardState[cellIndex] !== null) return;

        // اعمال حرکت بازیکن انسانی
        boardState[cellIndex] = मानवPlayerSymbol; // فرض می‌کنیم کاربر همیشه मानवPlayerSymbol است
        updateCellDOM(cellIndex, मानवPlayerSymbol);
        currentPlayer = मानवPlayerSymbol; // برای ارسال به endGame

        const winnerInfo = checkWin();
        if (winnerInfo.hasWinner) {
            endGame(false, winnerInfo.winningPlayer);
            return;
        } else if (boardState.every(cell => cell !== null)) {
            endGame(true, null);
            return;
        }

        // حالا بر اساس حالت بازی، تصمیم می‌گیریم چه کنیم
        if (currentGamemode === 'ai') {
            switchPlayerToAI(); // نوبت به AI داده می‌شود
            // اینجا یک تاخیر کوچک ایجاد می‌کنیم تا کاربر حرکتش را ببیند، سپس AI بازی کند
            setTimeout(aiMakeMove, 500); // AI بعد از نیم ثانیه حرکت می‌کند
        } else if (currentGamemode === 'online_pvp_host' || currentGamemode === 'online_pvp_guest') {
            // حرکت را به سرور ارسال کن
            sendMoveToServer(cellIndex);
            // و منتظر حرکت حریف از طریق polling بمان (یا نوتیفیکیشن)
            updateStatusMessage("حرکت شما ارسال شد. منتظر حریف...");
            gameActive = false; // موقتا بازی را غیرفعال کن تا سرور پاسخ دهد یا نوبت حریف شود
        }
    }

    function switchPlayerToAI() {
        currentPlayer = aiPlayerSymbol;
        updateStatusMessage(`نوبت کامپیوتر (${aiPlayerSymbol})...`);
        gameActive = false; // تا زمانی که AI حرکت نکرده، کاربر نتواند کلیک کند
    }
    
    function switchPlayerToHuman() {
        currentPlayer = मानवPlayerSymbol;
        updateStatusMessage(`نوبت شما (${मानवPlayerSymbol})`);
        gameActive = true;
    }


    function checkWin() { /* ... (بدون تغییر از نسخه قبلی که آبجکت برمی‌گرداند) ... */ }
    async function submitScoreToAPI(score, gameType, telegramInitData) { /* ... (بدون تغییر) ... */ }

    function endGame(isDraw, winner) {
        gameActive = false;
        if(gameBoardSection) gameBoardSection.classList.add('game-over'); // اصلاح شده

        let gameScore = 0; 
        let statusMessage = '';

        if (isDraw) {
            statusMessage = 'بازی مساوی شد! 😐';
            gameScore = (currentGamemode === 'ai' || currentGamemode === 'online_pvp_host' || currentGamemode === 'online_pvp_guest') ? 1 : 0; 
        } else {
            statusMessage = `بازیکن ${winner} برنده شد! 🎉`;
            if (winner === मानवPlayerSymbol) { 
                gameScore = 10; 
            } else { // کامپیوتر یا حریف آنلاین برنده شده
                gameScore = 0; 
            }
        }
        updateStatusMessage(statusMessage);
        if (currentGamemode !== 'local_pvp') { // فقط برای AI و آنلاین امتیاز ثبت کن
            if (tg && tg.initData) {
                submitScoreToAPI(gameScore, currentGamemode, tg.initData);
            } else {
                updateStatusMessage(statusMessage + " (امتیاز در حالت تست ثبت نمی‌شود)");
            }
        }
        stopOnlineGamePolling(); // اگر بازی آنلاین بود، polling را متوقف کن
    }
    
    // ---------- توابع مربوط به AI (فعلاً خیلی ساده) ----------
    async function aiMakeMove() {
        if (!gameActive && currentPlayer === aiPlayerSymbol) {
            // TODO: اینجا باید API مربوط به AI صدا زده شود
            // فعلاً یک حرکت تصادفی ساده انجام می‌دهیم
            const availableCells = boardState.map((val, idx) => val === null ? idx : null).filter(val => val !== null);
            if (availableCells.length > 0) {
                const randomIndex = Math.floor(Math.random() * availableCells.length);
                const aiMoveIndex = availableCells[randomIndex];
                
                boardState[aiMoveIndex] = aiPlayerSymbol;
                updateCellDOM(aiMoveIndex, aiPlayerSymbol);

                const winnerInfo = checkWin();
                if (winnerInfo.hasWinner) {
                    endGame(false, winnerInfo.winningPlayer);
                } else if (boardState.every(cell => cell !== null)) {
                    endGame(true, null);
                } else {
                    switchPlayerToHuman(); // نوبت بازیکن انسانی
                }
            }
        }
    }

    // ---------- توابع مربوط به بازی آنلاین (فعلاً Placeholder) ----------
    async function createOnlineGame() {
        updateStatusMessage("در حال ایجاد بازی آنلاین...");
        // TODO: API /api/online_game/create را صدا بزن
        // onlineGameId را از پاسخ بگیر و نمایش بده
        // startOnlineGamePolling();
        // initializeNewGame('online_pvp_host'); // یا بعد از دریافت پاسخ موفق
        // मानवPlayerSymbol = PLAYER_X; aiPlayerSymbol = PLAYER_O; (اگر هاست همیشه X است)
        alert("قابلیت ایجاد بازی آنلاین هنوز پیاده‌سازی نشده است.");
        showSection(gameModeSelectionSection); // برگرد به منوی اصلی
    }

    async function joinOnlineGame() {
        const gameId = joinGameIdInput.value.trim();
        if (!gameId) {
            alert("لطفاً کد بازی را وارد کنید.");
            return;
        }
        updateStatusMessage(`در حال پیوستن به بازی ${gameId}...`);
        // TODO: API /api/online_game/join را صدا بزن
        // onlineGameId = gameId;
        // startOnlineGamePolling();
        // initializeNewGame('online_pvp_guest'); // یا بعد از دریافت پاسخ موفق
        // मानवPlayerSymbol = PLAYER_O; aiPlayerSymbol = PLAYER_X; (اگر مهمان همیشه O است)
        alert("قابلیت پیوستن به بازی آنلاین هنوز پیاده‌سازی نشده است.");
        showSection(gameModeSelectionSection); // برگرد به منوی اصلی
    }

    async function sendMoveToServer(cellIndex) {
        console.log(`Sending move ${cellIndex} for game ${onlineGameId} to server...`);
        // TODO: API /api/online_game/move را صدا بزن
        // بدنه درخواست شامل: gameId, playerId (از initData), cellIndex
    }

    async function fetchOnlineGameStatus() {
        if (!onlineGameId || !gameActive) return; // یا شاید gameActive اینجا مهم نباشه
        console.log(`Polling for game status: ${onlineGameId}`);
        // TODO: API /api/online_game/status را صدا بزن
        // وضعیت جدید boardState و currentPlayer را بگیر
        // اگر تغییر کرده بود، صفحه را آپدیت کن
        // اگر نوبت ما بود، gameActive = true;
    }
    
    function startOnlineGamePolling() {
        if (onlineGamePollingInterval) clearInterval(onlineGamePollingInterval);
        // onlineGamePollingInterval = setInterval(fetchOnlineGameStatus, 3000); // هر ۳ ثانیه
    }

    function stopOnlineGamePolling() {
        if (onlineGamePollingInterval) {
            clearInterval(onlineGamePollingInterval);
            onlineGamePollingInterval = null;
        }
    }


    // ---------- توابع لیدربورد (بدون تغییر) ----------
    function applyTelegramTheme() { /* ... */ }
    async function fetchLeaderboard() { /* ... */ }
    function displayLeaderboard(leaderboardArray) { /* ... */ }
    function showLeaderboard() {
        if(leaderboardSection) leaderboardSection.classList.remove('hidden');
        fetchLeaderboard(); 
    }
    function hideLeaderboard() {
        if(leaderboardSection) leaderboardSection.classList.add('hidden');
    }
    

    // ---------- شروع اجرای اولیه و راه‌اندازی بازی ----------
    function initializeApp() {
        createBoardDOM(); // فقط یکبار DOM برد ساخته می‌شود

        // Event Listeners برای دکمه‌های انتخاب حالت
        if (playAiButton) {
            playAiButton.addEventListener('click', () => {
                मानवPlayerSymbol = PLAYER_X; // کاربر X است
                aiPlayerSymbol = PLAYER_O;   // کامپیوتر O است
                initializeNewGame('ai');
            });
        }
        if (createOnlineGameButton) {
            createOnlineGameButton.addEventListener('click', createOnlineGame);
        }
        if (joinOnlineGameButton) {
            joinOnlineGameButton.addEventListener('click', joinOnlineGame);
        }
        if (showLeaderboardFromMenuButton) {
            showLeaderboardFromMenuButton.addEventListener('click', () => {
                showSection(leaderboardSection); // بخش لیدربورد را نشان بده
            });
        }

        // Event Listener برای دکمه "شروع مجدد / خروج" داخل بازی
        // عملکرد این دکمه بسته به حالت بازی می‌تواند متفاوت باشد
        restartButton.addEventListener('click', () => {
            if (currentGamemode === 'ai') {
                initializeNewGame('ai'); // ریستارت بازی با AI
            } else if (currentGamemode && currentGamemode.startsWith('online_pvp')) {
                // TODO: منطق خروج از بازی آنلاین یا پیشنهاد بازی جدید
                stopOnlineGamePolling();
                onlineGameId = null;
                showSection(gameModeSelectionSection); // برگرد به منوی انتخاب حالت
                updateGameInfoMessage("");
            } else {
                // اگر در هیچ حالتی نبودیم (که نباید اتفاق بیفتد)
                showSection(gameModeSelectionSection);
            }
        });

        // Event Listener برای بستن لیدربورد
        if (closeLeaderboardButton) {
            closeLeaderboardButton.addEventListener('click', () => {
                // اگر در منوی اصلی هستیم، به منو برگرد، اگر در بازی هستیم، به بازی
                if (gameBoardSection.classList.contains('hidden')) {
                    showSection(gameModeSelectionSection);
                } else {
                    showSection(gameBoardSection);
                }
            });
        }

        if (tg) {
            tg.ready(); 
            applyTelegramTheme(); 
            tg.onEvent('themeChanged', applyTelegramTheme); 
            console.log("Telegram WebApp API initialized.");
            if (tg.initData) console.log("Raw initData:", tg.initData);
        } else {
            console.warn("Telegram WebApp API not available. Running in standalone browser mode.");
        }
        
        showSection(gameModeSelectionSection); // در ابتدا صفحه انتخاب حالت را نشان بده
    }

    initializeApp(); 
});
