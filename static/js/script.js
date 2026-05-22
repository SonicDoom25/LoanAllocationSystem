// AegisFund AI Frontend Scripts

console.log("AegisFund AI initialized.");

document.addEventListener("DOMContentLoaded", () => {

    // Fade-in animation
    document.body.classList.add("loaded");

    // Smooth card hover effect
    const cards =
      document.querySelectorAll(".dashboard-card");

    cards.forEach(card => {

        card.addEventListener("mouseenter", () => {
            card.style.transform =
              "translateY(-6px)";
        });

        card.addEventListener("mouseleave", () => {
            card.style.transform =
              "translateY(0px)";
        });

    });

});