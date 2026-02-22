/**
 * Spielgruppe Pumuckl — Accessibility enhancements for Chainlit
 *
 * This script runs after the page loads and makes three changes:
 *
 * 1. Injects a "Skip to chat" link as the first focusable element so keyboard
 *    users can bypass the header and jump straight to the message input.
 *
 * 2. Adds aria-live="polite" to the message list container so screen readers
 *    announce new agent replies without requiring a focus change.
 *
 * 3. Observes the message list for newly completed agent messages and moves
 *    keyboard focus to the latest one so screen reader users can read it
 *    immediately after it appears.
 *
 * NOTE: Chainlit renders a React app, so the DOM is not fully available on
 * DOMContentLoaded. We use a MutationObserver to wait for the message
 * container to appear before attaching further observers.
 */

(function () {
  "use strict";

  // ── 1. Skip-to-content link ─────────────────────────────────────────────

  function injectSkipLink() {
    if (document.getElementById("skip-to-chat")) return; // already injected

    const link = document.createElement("a");
    link.id = "skip-to-chat";
    link.href = "#chat-input";
    link.textContent = "Zum Chat springen / Skip to chat";

    // Clicking moves focus to the textarea inside #chat-input
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const target =
        document.querySelector("#chat-input textarea") ||
        document.querySelector("[data-testid='chat-input'] textarea") ||
        document.querySelector("textarea");
      if (target) {
        target.focus();
      }
    });

    document.body.insertBefore(link, document.body.firstChild);
  }

  // ── 2. ARIA live region on the message list ──────────────────────────────

  /**
   * Selectors to try for the message list container.
   * Chainlit's class names may change between versions; list several candidates.
   */
  const MESSAGE_LIST_SELECTORS = [
    "[data-testid='message-list']",
    ".message-list",
    "[class*='MessageList']",
    "[class*='messages']",
    ".cl-message-list",
  ];

  function findMessageList() {
    for (const sel of MESSAGE_LIST_SELECTORS) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  function applyLiveRegion(container) {
    if (container.dataset.liveRegionApplied) return;
    container.setAttribute("aria-live", "polite");
    container.setAttribute("aria-atomic", "false");
    container.setAttribute("aria-relevant", "additions");
    container.dataset.liveRegionApplied = "true";
  }

  // ── 3. Focus management after agent replies ──────────────────────────────

  /**
   * Selectors for individual assistant message elements.
   * We look for the last one after a new addition.
   */
  const ASSISTANT_MESSAGE_SELECTORS = [
    "[data-testid='assistant-message']",
    "[data-author='assistant']",
    "[class*='assistant']",
    ".cl-message[data-role='assistant']",
  ];

  let _lastFocusedMessage = null;

  function focusLatestAssistantMessage(container) {
    let latest = null;
    for (const sel of ASSISTANT_MESSAGE_SELECTORS) {
      const all = container.querySelectorAll(sel);
      if (all.length > 0) {
        latest = all[all.length - 1];
        break;
      }
    }

    // Fallback: grab the last direct child of the message list
    if (!latest) {
      const children = container.children;
      latest = children[children.length - 1] || null;
    }

    if (!latest || latest === _lastFocusedMessage) return;

    _lastFocusedMessage = latest;
    // tabindex="-1" lets us focus() without adding the element to tab order
    latest.setAttribute("tabindex", "-1");
    latest.focus({ preventScroll: false });
  }

  // ── Bootstrap: wait for Chainlit to render, then attach everything ───────

  let _messageListObserver = null;

  function onMessageListFound(messageList) {
    applyLiveRegion(messageList);

    // Watch for new messages being added
    _messageListObserver = new MutationObserver(function (mutations) {
      const hasAdditions = mutations.some(function (m) {
        return m.addedNodes.length > 0;
      });
      if (hasAdditions) {
        // Small delay lets Chainlit finish rendering the new message element
        setTimeout(function () {
          focusLatestAssistantMessage(messageList);
        }, 150);
      }
    });

    _messageListObserver.observe(messageList, { childList: true, subtree: true });
  }

  // Watch the body for the message list to appear (Chainlit is a SPA)
  const _rootObserver = new MutationObserver(function () {
    injectSkipLink();

    const messageList = findMessageList();
    if (messageList) {
      onMessageListFound(messageList);
      // No need to keep watching once we found the container
      _rootObserver.disconnect();
    }
  });

  _rootObserver.observe(document.body, { childList: true, subtree: true });

  // Also try immediately in case the app rendered synchronously
  injectSkipLink();
  const messageList = findMessageList();
  if (messageList) {
    onMessageListFound(messageList);
    _rootObserver.disconnect();
  }
})();
