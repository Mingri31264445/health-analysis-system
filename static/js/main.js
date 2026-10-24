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

  const analysisCards = document.querySelectorAll("[data-module-result]");
  const analysisResult = document.getElementById("analysis-result");

  if (analysisCards.length === 4 && analysisResult) {
    const states = Array.from(analysisCards, (card) => card.dataset.moduleResult);
    analysisCards.forEach((card) => {
      const state = card.dataset.moduleResult;
      card.querySelector(".result-badge").textContent =
        state === "yes" ? "有" : state === "no" ? "無" : "未完成";
    });

    if (states.every((state) => state === "yes" || state === "no")) {
      const positiveCount = states.filter((state) => state === "yes").length;
      const light = positiveCount === 0 ? "green" : positiveCount <= 2 ? "yellow" : "red";
      const indicator = analysisResult.closest(".analysis-indicator");
      indicator.classList.add("has-result");
      indicator.querySelector(`[data-light="${light}"]`).closest(".analysis-light-row").classList.add("is-active");
      analysisResult.textContent = `目前狀態：${{ green: "綠燈｜無異常項目", yellow: "黃燈｜部分項目需留意", red: "紅燈｜多項結果需留意" }[light]}`;
    }
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

  const scrollToDashboardAnchor = () => {
    const target = document.querySelector(window.location.hash);

    if (!target) return;

    window.setTimeout(() => {
      target.scrollIntoView({
        block: "start",
        inline: "nearest",
      });
    }, 80);
  };

  if (
    window.location.hash === "#subject-tracker" ||
    window.location.hash === "#subject-list" ||
    window.location.hash === "#recent-records"
  ) {
    scrollToDashboardAnchor();
  }

  const recordFilterLinks = document.querySelectorAll(
    ".dashboard-record-filters a[data-record-filter]",
  );
  const recordItems = document.querySelectorAll(".dashboard-record-item");
  const recordEmpty = document.querySelector(".dashboard-record-filter-empty");
  const maxVisibleRecords = 6;

  const applyRecordFilter = (filterKey, updateUrl = true) => {
    if (!recordItems.length) return;

    let visibleCount = 0;

    recordItems.forEach((item) => {
      const itemType = item.getAttribute("data-record-type");
      const matches = filterKey === "all" || itemType === filterKey;
      const shouldShow = matches && visibleCount < maxVisibleRecords;

      item.hidden = !shouldShow;

      if (matches) {
        visibleCount += 1;
      }
    });

    recordFilterLinks.forEach((link) => {
      link.classList.toggle(
        "is-active",
        link.getAttribute("data-record-filter") === filterKey,
      );
    });

    if (recordEmpty) {
      recordEmpty.hidden = visibleCount !== 0;
    }

    if (updateUrl) {
      const url = new URL(window.location.href);

      if (filterKey === "all") {
        url.searchParams.delete("record_type");
      } else {
        url.searchParams.set("record_type", filterKey);
      }

      window.history.replaceState({}, "", url);
    }
  };

  if (recordFilterLinks.length) {
    const initialFilter =
      new URL(window.location.href).searchParams.get("record_type") || "all";

    applyRecordFilter(initialFilter, false);

    recordFilterLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        applyRecordFilter(link.getAttribute("data-record-filter") || "all");
      });
    });
  }

  const subjectTabs = document.querySelectorAll("[data-subject-tab]");
  const subjectPanels = document.querySelectorAll("[data-subject-panel]");

  const selectSubject = (panelId) => {
    subjectTabs.forEach((tab) => {
      const isActive = tab.getAttribute("data-subject-tab") === panelId;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    subjectPanels.forEach((panel) => {
      const isActive = panel.getAttribute("data-subject-panel") === panelId;
      panel.hidden = !isActive;
      panel.classList.toggle("is-active", isActive);
    });
  };

  if (subjectTabs.length && subjectPanels.length) {
    subjectTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        selectSubject(tab.getAttribute("data-subject-tab"));
      });
    });
  }

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
    ".start-card, .analysis-module-card, .login-btn, .nav-dropdown-menu a, .system-nav-links a, .system-secondary, a.system-submit, .system-switch a, .forgot-link",
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
