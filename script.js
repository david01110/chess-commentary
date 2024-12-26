
console.log("JavaScript wird geladen!");
const board = document.getElementById('board');
const notationDiv = document.getElementById('notation');
const commentInput = document.getElementById('comment');
const evaluationInput = document.getElementById('evaluation');

const ground = Chessground(board, { draggable: false });
const game = new Chess();
const comments = [];
const evaluations = [];

let moves = [];

// Lade Partie-Daten von Lichess
async function loadGame() {
    const response = await fetch('https://lichess.org/api/broadcast/6Mwn3xBh/0iQYc2zB');
    const data = await response.json();
    moves = data.moves.split(' '); // Züge laden
    renderMoves();
}

// Zeige Notation und mache sie klickbar
function renderMoves() {
    notationDiv.innerHTML = '';
    moves.forEach((move, index) => {
        const moveButton = document.createElement('button');
        moveButton.textContent = `${index + 1}. ${move}`;
        moveButton.onclick = () => displayPosition(index);
        notationDiv.appendChild(moveButton);
    });
}

// Zeige Stellung nach einem Zug
function displayPosition(index) {
    game.reset();
    for (let i = 0; i <= index; i++) {
        game.move(moves[i]);
    }
    ground.set({ fen: game.fen() });
    commentInput.value = comments[index] || '';
    evaluationInput.value = evaluations[index] || '';
}

// Kommentar speichern
function saveComment() {
    const index = getCurrentMoveIndex();
    comments[index] = commentInput.value;
    alert(`Kommentar für Zug ${index + 1} gespeichert!`);
}

// Bewertung speichern
function saveEvaluation() {
    const index = getCurrentMoveIndex();
    evaluations[index] = evaluationInput.value;
    alert(`Bewertung für Zug ${index + 1} gespeichert!`);
}

// Hilfsfunktion: Aktueller Zug
function getCurrentMoveIndex() {
    return game.history().length - 1;
}

loadGame();
