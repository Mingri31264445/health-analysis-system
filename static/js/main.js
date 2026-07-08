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
      rootMargin: "0px 0px -40px 0px",
    },
  );

  revealElements.forEach((el) => observer.observe(el));

  const dashboardItems = document.querySelectorAll(".dashboard-reveal");

  if (dashboardItems.length) {
    dashboardItems.forEach((item, index) => {
      setTimeout(
        () => {
          item.classList.add("dashboard-show");
        },
        350 + index * 180,
      );
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
        threshold: 0.2,
      },
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

            const target = parseInt(
              scoreElement.getAttribute("data-target"),
              10,
            );
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
        threshold: 0.4,
      },
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

  const passwordToggles = document.querySelectorAll(".password-toggle");

  passwordToggles.forEach((button) => {
    button.addEventListener("click", () => {
      const wrapper = button.closest(".password-input-wrap");
      const input = wrapper ? wrapper.querySelector("input") : null;

      if (!input) return;

      const shouldShow = input.type === "password";
      input.type = shouldShow ? "text" : "password";
      button.classList.toggle("is-visible", shouldShow);
      button.setAttribute("aria-label", shouldShow ? "隱藏密碼" : "顯示密碼");
      button.setAttribute("aria-pressed", shouldShow ? "true" : "false");
    });
  });

  const showPageTransition = () => {
    document.body.classList.add("page-transitioning");
  };

  const transitionDelay = 150;

  const actionLinks = document.querySelectorAll(
    ".start-card, .analysis-module-card, .login-btn, .system-nav-links a, .system-secondary, a.system-submit, .system-switch a, .forgot-link",
  );

  const isInternalNavigation = (link) => {
    if (!link.href || link.target || link.hasAttribute("download"))
      return false;

    const url = new URL(link.href, window.location.href);
    const current = new URL(window.location.href);
    const isSamePageHash =
      url.origin === current.origin &&
      url.pathname === current.pathname &&
      url.search === current.search &&
      url.hash;

    return url.origin === current.origin && !isSamePageHash;
  };

  actionLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      link.classList.add("is-clicking");

      if (!isInternalNavigation(link)) return;

      event.preventDefault();
      showPageTransition();

      window.setTimeout(() => {
        window.location.href = link.href;
      }, transitionDelay);
    });
  });

  const forms = document.querySelectorAll(".system-form");

  forms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      const submitButton = form.querySelector(".system-submit");

      if (!submitButton || submitButton.classList.contains("is-loading"))
        return;

      event.preventDefault();
      submitButton.setAttribute("aria-busy", "true");
      submitButton.classList.add("is-loading");
      submitButton.disabled = true;
      showPageTransition();

      window.setTimeout(() => {
        form.submit();
      }, transitionDelay);
    });
  });
});
