
// Set the wedding date (YYYY-MM-DD)
const weddingDate = new Date("2025-09-12T15:00:00").getTime();

function updateCountdown() {
  const now = new Date().getTime();
  const distance = weddingDate - now;

  if (distance <= 0) {
    document.getElementById("countdown").innerHTML = "🎉 It's wedding day!";
    return;
  }

  const days = Math.floor(distance / (1000 * 60 * 60 * 24));
  const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((distance % (1000 * 60)) / 1000);

  document.getElementById("countdown").innerHTML = 
    `⏳ ${days}d ${hours}h ${minutes}m ${seconds}s`;
}

// Update every second
setInterval(updateCountdown, 1000);
updateCountdown();
