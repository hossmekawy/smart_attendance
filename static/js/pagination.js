// Define the pagination component for Alpine.js
document.addEventListener('DOMContentLoaded', function() {
    // Make sure Alpine is available
    if (typeof Alpine !== 'undefined') {
        Alpine.data('pagination', function(currentPage, totalPages, endpoint, params) {
            return {
                currentPage: currentPage,
                totalPages: totalPages,
                endpoint: endpoint,
                params: params || {},

                hasPrev: function() {
                    return this.currentPage > 1;
                },

                hasNext: function() {
                    return this.currentPage < this.totalPages;
                },

                prevPageUrl: function() {
                    return this.getPageUrl(this.currentPage - 1);
                },

                nextPageUrl: function() {
                    return this.getPageUrl(this.currentPage + 1);
                },

                getPageUrl: function(page) {
                    // Create a copy of the params
                    const queryParams = {...this.params, page: page };

                    // Build the query string
                    const queryString = Object.keys(queryParams)
                        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(queryParams[key])}`)
                        .join('&');

                    return `${this.endpoint}?${queryString}`;
                },

                paginationItems: function() {
                    const items = [];
                    const leftCurrent = 2;
                    const rightCurrent = 2;

                    // Always include first page
                    items.push({ type: 'page', value: 1 });

                    // Calculate window of pages around current page
                    let windowStart = Math.max(2, this.currentPage - leftCurrent);
                    let windowEnd = Math.min(this.totalPages - 1, this.currentPage + rightCurrent);

                    // Adjust window to ensure minimum size
                    if (windowEnd < windowStart + leftCurrent + rightCurrent) {
                        windowStart = Math.max(2, windowEnd - leftCurrent - rightCurrent);
                    }

                    // Add ellipsis if needed before window
                    if (windowStart > 2) {
                        items.push({ type: 'ellipsis', value: null });
                    }

                    // Add pages in window
                    for (let i = windowStart; i <= windowEnd; i++) {
                        items.push({ type: 'page', value: i });
                    }

                    // Add ellipsis if needed after window
                    if (windowEnd < this.totalPages - 1) {
                        items.push({ type: 'ellipsis', value: null });
                    }

                    // Always include last page if not already included
                    if (this.totalPages > 1) {
                        items.push({ type: 'page', value: this.totalPages });
                    }

                    return items;
                }
            };
        });
    } else {
        console.error('Alpine.js is not loaded!');
    }
});