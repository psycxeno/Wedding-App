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

// Update countdown every second
setInterval(updateCountdown, 1000);
updateCountdown();

// Show/hide guests field based on attendance
document.addEventListener('DOMContentLoaded', function() {
  const attendingRadios = document.querySelectorAll('input[name="attending"]');
  const guestsGroup = document.getElementById('guests');
  
  attendingRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      if (this.value === 'true') {
        guestsGroup.style.display = 'block';
      } else {
        guestsGroup.style.display = 'none';
        guestsGroup.value = '0';
      }
    });
  });
}); 