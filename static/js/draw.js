document.addEventListener('DOMContentLoaded', () => {

    const canvas = document.getElementById('pixel-canvas');
    const ctx = canvas.getContext('2d');

    // --- Configuration ---
    const PIXEL_SIZE = 20;
    const GRID_WIDTH = 32;
    const GRID_HEIGHT = 32;
    const canvasWidth = PIXEL_SIZE * GRID_WIDTH;
    const canvasHeight = PIXEL_SIZE * GRID_HEIGHT;
    const GRID_COLOR = "#333";

    // --- State ---
    let selectedColor = '#FFFFFF'; // Default to white
    const colors = [
        '#FFFFFF', '#C1C1C1', '#EF130B', '#FF7100', '#FFE400', '#00CC00',
        '#00B2FF', '#231FD3', '#A300BA', '#634b35', '#000000', '#ff99aa'
    ];

    // --- Initialization ---
    function initialize() {
        // Set canvas dimensions
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;

        // Setup the color palette UI
        setupPalette();

        // Draw the initial grid
        drawGrid();

        // Add event listeners
        canvas.addEventListener('click', handleCanvasClick);
    }

    // --- UI Setup ---
    function setupPalette() {
        const paletteContainer = document.getElementById('color-palette');
        paletteContainer.innerHTML = ''; // Clear existing palette

        colors.forEach(color => {
            const colorDiv = document.createElement('div');
            colorDiv.style.backgroundColor = color;
            colorDiv.style.width = '40px';
            colorDiv.style.height = '40px';
            colorDiv.style.margin = '5px';
            colorDiv.style.cursor = 'pointer';
            colorDiv.style.border = '2px solid transparent';
            colorDiv.addEventListener('click', () => {
                selectedColor = color;
                // Update selected highlight
                document.querySelectorAll('#color-palette div').forEach(div => {
                    div.style.border = '2px solid transparent';
                });
                colorDiv.style.border = '2px solid #00B2FF';
            });
            paletteContainer.appendChild(colorDiv);
        });

        // Select the first color by default
        paletteContainer.firstChild.style.border = '2px solid #00B2FF';
    }

    // --- Drawing Functions ---
    function drawGrid() {
        ctx.strokeStyle = GRID_COLOR;
        ctx.lineWidth = 1;

        for (let x = 0; x <= canvasWidth; x += PIXEL_SIZE) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvasHeight);
            ctx.stroke();
        }

        for (let y = 0; y <= canvasHeight; y += PIXEL_SIZE) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvasWidth, y);
            ctx.stroke();
        }
    }

    function fillPixel(x, y, color) {
        ctx.fillStyle = color;
        ctx.fillRect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE);
        // Redraw grid over the pixel to maintain borders
        drawGrid();
    }

    // --- Event Handlers ---
    function handleCanvasClick(event) {
        // Get mouse coordinates relative to the canvas
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        // Calculate grid coordinates
        const gridX = Math.floor(mouseX / PIXEL_SIZE);
        const gridY = Math.floor(mouseY / PIXEL_SIZE);

        // Fill the pixel
        fillPixel(gridX, gridY, selectedColor);
    }

    // --- Start the app ---
    initialize();
});
