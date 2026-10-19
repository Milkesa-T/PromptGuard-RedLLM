(() => {
  document.addEventListener('DOMContentLoaded', () => {
    const navButton = document.querySelector('.nav-item[data-tab="rag-kb"]');
    const pane = document.getElementById('tab-rag-kb');
    const pageTitle = document.getElementById('page-title');
    const pageDesc = document.getElementById('page-desc');
    const summary = document.getElementById('rag-summary');
    const grid = document.getElementById('rag-doc-grid');
    const refreshButton = document.getElementById('rag-refresh-btn');
    const searchForm = document.getElementById('rag-search-form');
    const searchInput = document.getElementById('rag-search-input');
    const searchTopK = document.getElementById('rag-search-topk');
    const searchButton = document.getElementById('rag-search-btn');
    const searchClearButton = document.getElementById('rag-search-clear');
    const searchResults = document.getElementById('rag-search-results');
    const modal = document.getElementById('rag-chunk-modal');
    const modalTitle = document.getElementById('rag-modal-title');
    const modalMeta = document.getElementById('rag-modal-meta');
    const chunkList = document.getElementById('rag-chunk-list');
    const modalClose = document.getElementById('rag-modal-close');

    if (!navButton || !pane || !grid || !summary || !modal || !searchForm || !searchResults) return;

    const SEARCH_LIMIT = 10;
    const documentCache = new Map();
    let hasLoaded = false;
    let lastFocusedCard = null;
    let latestSearchId = 0;

    function makeElement(tagName, className, text) {
      const element = document.createElement(tagName);
      if (className) element.className = className;
      if (text !== undefined) element.textContent = text;
      return element;
    }

    function setPageHeading() {
      if (pageTitle) pageTitle.textContent = 'RAG Knowledge Base';
      if (pageDesc) pageDesc.textContent = 'Browse loaded documents and preview their indexed chunks.';
    }

    function setStatus(message, className = 'text-muted') {
      grid.replaceChildren(makeElement('p', `rag-state ${className}`, message));
    }

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }
      return response.json();
    }

    function searchChunks(query, topK) {
      return fetchJson('/api/rag/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK })
      });
    }

    function renderSearchResults(data, query) {
      searchResults.replaceChildren();
      const chunks = Array.isArray(data.chunks) ? data.chunks : [];
      const count = Number(data.matches_found);
      const matchCount = Number.isFinite(count) ? count : chunks.length;
      searchResults.appendChild(makeElement('h3', 'rag-search-heading', `${matchCount} matches for '${query}'`));

      if (chunks.length === 0) {
        searchResults.appendChild(makeElement('p', 'rag-state text-muted', 'No matches'));
        return;
      }

      chunks.forEach((chunk, index) => {
        const card = makeElement('article', 'card rag-result-card');
        const topLine = makeElement('div', 'rag-result-topline');
        topLine.appendChild(makeElement('span', 'badge badge-info', `Rank #${index + 1}`));
        const score = Number(chunk.similarity_score);
        if (Number.isFinite(score)) {
          topLine.appendChild(makeElement('span', 'rag-result-score', score.toFixed(3)));
        }
        card.appendChild(topLine);

        const documentName = String(chunk.doc_name || chunk.source || 'Unknown document');
        const documentButton = makeElement('button', 'rag-result-document', documentName);
        documentButton.type = 'button';
        documentButton.addEventListener('click', () => openSearchDocument(documentName, chunks));
        card.appendChild(documentButton);
        card.appendChild(makeElement('h4', 'rag-result-heading', chunk.heading || 'Document section'));

        const chunkIndex = chunk.chunk_index === undefined || chunk.chunk_index === null ? index : chunk.chunk_index;
        card.appendChild(makeElement('span', 'badge badge-info', `Chunk #${chunkIndex}`));

        if (Number.isFinite(score)) {
          const normalizedScore = Math.max(0, Math.min(1, score));
          const scoreBar = makeElement('div', 'rag-score-track');
          scoreBar.setAttribute('role', 'progressbar');
          scoreBar.setAttribute('aria-label', `Similarity ${score.toFixed(3)}`);
          scoreBar.setAttribute('aria-valuemin', '0');
          scoreBar.setAttribute('aria-valuemax', '1');
          scoreBar.setAttribute('aria-valuenow', String(normalizedScore));
          const scoreFill = makeElement('span', 'rag-score-fill');
          scoreFill.style.width = `${normalizedScore * 100}%`;
          scoreBar.appendChild(scoreFill);
          card.appendChild(scoreBar);
        }

        const fullText = String(chunk.text || '');
        const preview = makeElement('p', 'rag-result-text');
        const isLong = fullText.length > 200;
        preview.textContent = isLong ? `${fullText.slice(0, 200)}…` : fullText;
        card.appendChild(preview);

        if (isLong) {
          const toggle = makeElement('button', 'btn btn-xs btn-secondary', 'Show more');
          toggle.type = 'button';
          let expanded = false;
          toggle.addEventListener('click', () => {
            expanded = !expanded;
            preview.textContent = expanded ? fullText : `${fullText.slice(0, 200)}…`;
            toggle.textContent = expanded ? 'Show less' : 'Show more';
          });
          card.appendChild(toggle);
        }

        searchResults.appendChild(card);
      });
    }

    function openSearchDocument(name, resultChunks) {
      const normalizedName = normalizeDocumentName(name);
      let matchedDocument = null;
      documentCache.forEach((cachedDocument) => {
        if (normalizeDocumentName(cachedDocument.name) === normalizedName) {
          matchedDocument = cachedDocument;
        }
      });

      if (matchedDocument) {
        openDocument(matchedDocument, null);
        return;
      }

      const chunks = resultChunks.filter((chunk) =>
        normalizeDocumentName(chunk.doc_name || chunk.source) === normalizedName
      );
      sortChunks(chunks);
      openDocument({ name, chunks }, null);
    }

    async function runSearch(queryValue) {
      const query = String(queryValue === undefined ? searchInput.value : queryValue).trim();
      const requestId = ++latestSearchId;
      searchResults.hidden = false;

      if (!query) {
        searchButton.disabled = false;
        searchResults.replaceChildren(makeElement('p', 'rag-state text-muted', 'Enter a query to search the knowledge base.'));
        return;
      }

      const topK = Math.max(1, Math.min(SEARCH_LIMIT, Number(searchTopK.value) || 5));
      searchButton.disabled = true;
      searchResults.replaceChildren(makeElement('p', 'rag-state text-muted', 'Searching the knowledge base...'));

      try {
        const data = await searchChunks(query, topK);
        if (requestId !== latestSearchId) return;
        renderSearchResults(data, query);
      } catch (error) {
        if (requestId !== latestSearchId) return;
        searchResults.replaceChildren();
        const state = makeElement('div', 'rag-state rag-error');
        state.appendChild(makeElement('p', '', error.message || 'Search failed.'));
        const retryButton = makeElement('button', 'btn btn-secondary btn-sm', 'Retry');
        retryButton.type = 'button';
        retryButton.addEventListener('click', () => runSearch(query));
        state.appendChild(retryButton);
        searchResults.appendChild(state);
      } finally {
        if (requestId === latestSearchId) searchButton.disabled = false;
      }
    }

    function normalizeDocumentName(name) {
      return String(name || '').replace(/\\/g, '/').split('/').pop().toLowerCase();
    }

    function sortChunks(chunks) {
      chunks.sort((left, right) => {
        const leftIndex = Number(left.chunk_index);
        const rightIndex = Number(right.chunk_index);
        return (Number.isFinite(leftIndex) ? leftIndex : 0) - (Number.isFinite(rightIndex) ? rightIndex : 0);
      });
    }

    async function loadDocuments() {
      summary.textContent = 'Loading documents...';
      setStatus('Loading RAG documents...');
      refreshButton.disabled = true;

      try {
        const data = await fetchJson('/api/rag/documents');
        const documents = Array.isArray(data.documents) ? data.documents : [];
        const totalChunks = Number(data.total_chunks) || 0;
        const groupedChunks = [];

        if (totalChunks > 0 && documents.length > 0) {
          if (totalChunks <= SEARCH_LIMIT) {
            const result = await searchChunks('document', totalChunks);
            groupedChunks.push(...(Array.isArray(result.chunks) ? result.chunks : []));
          } else {
            const results = await Promise.all(documents.map((name) => searchChunks(name, SEARCH_LIMIT)));
            results.forEach((result) => {
              if (Array.isArray(result.chunks)) groupedChunks.push(...result.chunks);
            });
          }
        }

        documentCache.clear();
        documents.forEach((name) => {
          const safeName = String(name);
          documentCache.set(safeName, { name: safeName, chunks: [] });
        });

        const nameLookup = new Map();
        documentCache.forEach((document) => {
          nameLookup.set(normalizeDocumentName(document.name), document);
        });

        groupedChunks.forEach((chunk) => {
          const groupName = String(chunk.doc_name || chunk.source || 'Unknown document');
          const document = nameLookup.get(normalizeDocumentName(groupName));
          if (document) document.chunks.push(chunk);
        });

        documentCache.forEach((document) => sortChunks(document.chunks));
        summary.textContent = `${documents.length} document${documents.length === 1 ? '' : 's'} · ${totalChunks} total chunks`;
        renderCards();
        hasLoaded = true;
      } catch (error) {
        summary.textContent = 'Unable to load RAG documents.';
        grid.replaceChildren();
        const state = makeElement('div', 'rag-state rag-error');
        state.appendChild(makeElement('p', '', error.message || 'A network error occurred.'));
        const retryButton = makeElement('button', 'btn btn-secondary btn-sm', 'Retry');
        retryButton.type = 'button';
        retryButton.addEventListener('click', loadDocuments);
        state.appendChild(retryButton);
        grid.appendChild(state);
      } finally {
        refreshButton.disabled = false;
      }
    }

    function renderCards() {
      grid.replaceChildren();
      if (documentCache.size === 0) {
        setStatus('No documents loaded');
        return;
      }

      documentCache.forEach((document) => {
        const card = makeElement('button', 'card rag-doc-card');
        card.type = 'button';
        card.tabIndex = 0;
        card.setAttribute('aria-label', `Open ${document.name}, ${document.chunks.length} chunks`);
        card.addEventListener('click', () => openDocument(document, card));

        const cardTop = makeElement('div', 'rag-doc-card-top');
        cardTop.appendChild(makeElement('span', 'rag-doc-icon', '📄'));
        const extension = document.name.split('.').pop().toLowerCase();
        const typeBadge = makeElement('span', 'badge badge-info', `.${extension}`);
        cardTop.appendChild(typeBadge);
        card.appendChild(cardTop);

        card.appendChild(makeElement('h4', 'rag-doc-name', document.name));
        card.appendChild(makeElement('span', 'badge badge-info rag-chunk-count', `${document.chunks.length} chunks`));
        const firstChunk = document.chunks[0];
        const preview = firstChunk ? String(firstChunk.text || '').slice(0, 150) : 'No chunk preview available.';
        card.appendChild(makeElement('p', 'rag-doc-preview', preview));
        grid.appendChild(card);
      });
    }

    function openDocument(document, card) {
      lastFocusedCard = card;
      modalTitle.textContent = document.name;
      modalMeta.textContent = `${document.chunks.length} chunk${document.chunks.length === 1 ? '' : 's'}`;
      chunkList.replaceChildren();

      if (document.chunks.length === 0) {
        chunkList.appendChild(makeElement('p', 'text-muted', 'No chunks are available for this document.'));
      }

      document.chunks.forEach((chunk, index) => {
        const block = makeElement('article', 'rag-chunk-block');
        const header = makeElement('div', 'rag-chunk-heading-row');
        header.appendChild(makeElement('h4', '', chunk.heading || 'Document section'));
        const chunkIndex = chunk.chunk_index === undefined || chunk.chunk_index === null ? index : chunk.chunk_index;
        header.appendChild(makeElement('span', 'badge badge-info', `Chunk #${chunkIndex}`));
        block.appendChild(header);

        const fullText = String(chunk.text || '');
        const text = makeElement('p', 'rag-chunk-text');
        const isLong = fullText.length > 200;
        text.textContent = isLong ? `${fullText.slice(0, 200)}…` : fullText;
        block.appendChild(text);

        if (isLong) {
          const toggle = makeElement('button', 'btn btn-xs btn-secondary rag-show-more', 'Show more');
          toggle.type = 'button';
          let expanded = false;
          toggle.addEventListener('click', () => {
            expanded = !expanded;
            text.textContent = expanded ? fullText : `${fullText.slice(0, 200)}…`;
            toggle.textContent = expanded ? 'Show less' : 'Show more';
          });
          block.appendChild(toggle);
        }

        chunkList.appendChild(block);
      });

      modal.classList.add('active');
      modalClose.focus();
    }

    function closeModal() {
      modal.classList.remove('active');
      if (lastFocusedCard) lastFocusedCard.focus();
    }

    navButton.addEventListener('click', () => {
      setPageHeading();
      if (!hasLoaded) loadDocuments();
    });
    searchForm.addEventListener('submit', (event) => {
      event.preventDefault();
      runSearch();
    });
    searchClearButton.addEventListener('click', () => {
      latestSearchId += 1;
      searchInput.value = '';
      searchButton.disabled = false;
      searchResults.replaceChildren();
      searchResults.hidden = true;
    });
    refreshButton.addEventListener('click', loadDocuments);
    modalClose.addEventListener('click', closeModal);
    modal.addEventListener('click', (event) => {
      if (event.target === modal) closeModal();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && modal.classList.contains('active')) closeModal();
    });
  });
})();
