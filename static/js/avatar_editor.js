document.addEventListener('DOMContentLoaded', () => {
    // --- Setup & Config ---
    const canvas = document.getElementById('avatar-canvas');
    const colorPicker = document.getElementById('color-picker');
    const gridToggle = document.getElementById('grid-toggle');
    const brushSlider = document.getElementById('brush-slider');
    const brushSizeDisplay = document.getElementById('brush-size-display');
    const clearButton = document.getElementById('clear-button');
    const downloadBtn = document.getElementById('download-btn'); // New element
    const avatarForm = document.getElementById('avatar-form');
    const avatarDataInput = document.getElementById('avatar-data-input');
    const ctx = canvas.getContext('2d');

    const GRID_DIM = 32;
    const GRID_COLOR = "#CCCCCC";
    canvas.width = GRID_DIM;
    canvas.height = GRID_DIM;
    canvas.style.width = '480px';
    canvas.style.height = '480px';
    canvas.style.imageRendering = 'pixelated';
    
    let avatarData = currentAvatarData || Array(GRID_DIM).fill(null).map(() => Array(GRID_DIM).fill('#FFFFFF'));

    // --- State Management ---
    let selectedColor = colorPicker.value;
    let brushSize = 1;
    let isDrawing = false;

    // --- Drawing & Canvas Functions ---
    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR;
        ctx.lineWidth = 0.05;
        for (let i = 0; i <= GRID_DIM; i++) {
            ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, GRID_DIM); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(GRID_DIM, i); ctx.stroke();
        }
    }

    function redrawCanvas() {
        ctx.clearRect(0, 0, GRID_DIM, GRID_DIM);
        for (let y = 0; y < GRID_DIM; y++) {
            for (let x = 0; x < GRID_DIM; x++) {
                ctx.fillStyle = avatarData[y][x] || '#FFFFFF';
                ctx.fillRect(x, y, 1, 1);
            }
        }
        if (gridToggle.checked) {
            drawGrid();
        }
    }

    function applyBrush(centerX, centerY) {
        const radius = Math.floor((brushSize - 1) / 2);
        for (let y = centerY - radius; y <= centerY + radius; y++) {
            for (let x = centerX - radius; x <= centerX + radius; x++) {
                placePixel(x, y);
            }
        }
    }

    function placePixel(gridX, gridY) {
        if (gridX < 0 || gridX >= GRID_DIM || gridY < 0 || gridY >= GRID_DIM) return;
        if (avatarData[gridY][gridX] === selectedColor) return;
        avatarData[gridY][gridX] = selectedColor;
    }
    
    // --- Event Listeners Setup ---
    function initialize() {
        for(let r=0; r < GRID_DIM; r++) {
            for (let c=0; c < GRID_DIM; c++) {
                if(avatarData[r][c] === null) {
                    avatarData[r][c] = '#FFFFFF';
                }
            }
        }
        redrawCanvas();

        colorPicker.addEventListener('input', (e) => selectedColor = e.target.value);
        gridToggle.addEventListener('change', redrawCanvas);
        clearButton.addEventListener('click', () => {
            avatarData = Array(GRID_DIM).fill(null).map(() => Array(GRID_DIM).fill('#FFFFFF'));
            redrawCanvas();
        });
        
        brushSlider.addEventListener('input', (e) => {
            brushSize = parseInt(e.target.value, 10);
            brushSizeDisplay.textContent = brushSize;
        });
        
        // NEW: Download button listener
        downloadBtn.addEventListener('click', () => {
            const link = document.createElement('a');
            link.download = 'avatar.png';
            // This captures the internal 32x32 canvas, not the scaled display version
            link.href = canvas.toDataURL('image/png');
            link.click();
        });

        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            applyBrush(getCoords(e).x, getCoords(e).y);
            redrawCanvas();
        });
        canvas.addEventListener('mousemove', (e) => {
            if (isDrawing) {
                applyBrush(getCoords(e).x, getCoords(e).y);
                redrawCanvas();
            }
        });
        document.addEventListener('mouseup', () => isDrawing = false);
        canvas.addEventListener('mouseleave', () => isDrawing = false);
        
        avatarForm.addEventListener('submit', () => {
            avatarDataInput.value = JSON.stringify(avatarData);
        });
    }

    function getCoords(event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        const xRatio = mouseX / rect.width;
        const yRatio = mouseY / rect.height;
        const gridX = Math.floor(xRatio * GRID_DIM);
        const gridY = Math.floor(yRatio * GRID_DIM);
        return { x: gridX, y: gridY };
    }
    
    initialize();
});