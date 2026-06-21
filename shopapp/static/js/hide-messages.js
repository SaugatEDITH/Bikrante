document.addEventListener("DOMContentLoaded", function () {
  const messagesContainer = document.querySelector(".messages");
  if (messagesContainer) {
    setTimeout(() => {
      messagesContainer.style.transition = "opacity 0.8s ease";
      messagesContainer.style.opacity = "0";
      setTimeout(() => {
        messagesContainer.classList.add("hidden"); // Add the hidden class
      }, 500); // Wait for the fade-out transition to complete
    }, 5000); // Hide after 5 seconds
  }
});
