document.addEventListener("DOMContentLoaded", function () {
    const revealElements = document.querySelectorAll(".reveal");

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("show");
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.12,
            rootMargin: "0px 0px -40px 0px"
        }
    );

    revealElements.forEach((el) => observer.observe(el));

    const dashboardItems = document.querySelectorAll(".dashboard-reveal");

    if (dashboardItems.length) {
        dashboardItems.forEach((item, index) => {
            setTimeout(() => {
                item.classList.add("dashboard-show");
            }, 350 + index * 180);
        });
    }

    const resultCards = document.querySelectorAll(".result-reveal");

    if (resultCards.length) {
        const resultObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("result-active");
                        resultObserver.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.2
            }
        );

        resultCards.forEach((card) => resultObserver.observe(card));
    }

    const scoreElement = document.getElementById("health-score");

    if (scoreElement) {
        let animated = false;

        const scoreObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting && !animated) {
                        animated = true;

                        const target = parseInt(scoreElement.getAttribute("data-target"), 10);
                        let current = 0;
                        const duration = 1600;
                        const stepTime = 20;
                        const steps = duration / stepTime;
                        const increment = target / steps;

                        const counter = setInterval(() => {
                            current += increment;

                            if (current >= target) {
                                scoreElement.textContent = target;
                                clearInterval(counter);
                            } else {
                                scoreElement.textContent = Math.floor(current);
                            }
                        }, stepTime);

                        scoreObserver.unobserve(scoreElement);
                    }
                });
            },
            {
                threshold: 0.4
            }
        );

        scoreObserver.observe(scoreElement);
    }

    const navbar = document.querySelector(".navbar");

    const handleNavbarScroll = () => {
        if (!navbar) return;

        if (window.scrollY > 20) {
            navbar.classList.add("scrolled");
        } else {
            navbar.classList.remove("scrolled");
        }
    };

    handleNavbarScroll();
    window.addEventListener("scroll", handleNavbarScroll);
});