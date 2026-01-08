// Friendly Fire Movie Tracker - Frontend JavaScript

// Global variables
let moviesData = [];
let dataTable = null;

// Service name mapping
const serviceNames = {
    'netflix': 'Netflix',
    'prime': 'Prime Video',
    'disney': 'Disney+',
    'hbo': 'HBO Max',
    'hulu': 'Hulu',
    'apple': 'Apple TV+',
    'paramount': 'Paramount+',
    'peacock': 'Peacock',
    'mubi': 'MUBI',
    'stan': 'Stan'
};

// Initialize app when DOM is ready
$(document).ready(function() {
    loadMovieData();
    setupEventListeners();
});

// Load movie data from JSON
async function loadMovieData() {
    try {
        // Load main movies data
        const response = await fetch('data/movies.json');

        if (!response.ok) {
            throw new Error('Failed to load movie data');
        }

        const data = await response.json();
        moviesData = data.movies || [];

        // Update last updated timestamp
        updateLastUpdated(data.last_updated);

        // Update statistics
        updateStatistics(data);

        // Render filters based on available data
        renderServiceFilters(getAvailableSubscriptionServices());

        // Load metadata
        loadMetadata();

        // Initialize table
        initializeTable();

        // Hide loading, show table
        $('#loading').hide();
        $('#table-container').show();

    } catch (error) {
        console.error('Error loading movie data:', error);
        $('#loading').hide();
        $('#error').show();
    }
}

// Load metadata
async function loadMetadata() {
    try {
        const response = await fetch('data/metadata.json');
        if (response.ok) {
            const metadata = await response.json();
            console.log('Metadata loaded:', metadata);
        }
    } catch (error) {
        console.warn('Could not load metadata:', error);
    }
}

// Update last updated timestamp
function updateLastUpdated(timestamp) {
    if (!timestamp) return;

    const date = new Date(timestamp);
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'UTC'
    };

    const formatted = date.toLocaleString('en-US', options) + ' UTC';
    $('#last-updated').text(`Last updated: ${formatted}`);
}

// Update statistics
function updateStatistics(data) {
    const totalMovies = data.total_movies || moviesData.length;
    const availableStreaming = moviesData.filter(m =>
        m.streaming_options && m.streaming_options.length > 0
    ).length;

    $('#total-movies').text(totalMovies);
    $('#available-streaming').text(availableStreaming);
}

// Initialize DataTable
function initializeTable() {
    // Prepare table data with raw values for sorting
    const tableData = moviesData.map(movie => [
        formatEpisodeNumber(movie.episode_number, movie.episode_url),
        movie.title || '',
        formatPlot(movie.plot),
        movie.year || '',
        formatRating(movie.imdb_rating, movie.imdb_votes),
        movie.ar,  // Raw value for sorting
        movie.br,  // Raw value for sorting
        movie.jr,  // Raw value for sorting
        movie.rating,  // Raw value for sorting
        formatStreamingOptions(movie.streaming_options),
        formatLinks(movie.imdb_url, movie.imdb_id)
    ]);

    // Initialize DataTable
    dataTable = $('#movies-table').DataTable({
        data: tableData,
        responsive: true,
        pageLength: 25,
        order: [[0, 'desc']], // Sort by episode number descending (newest first)
        language: {
            search: "Search movies:",
            lengthMenu: "Show _MENU_ movies per page",
            info: "Showing _START_ to _END_ of _TOTAL_ movies",
            infoEmpty: "No movies found",
            infoFiltered: "(filtered from _MAX_ total movies)"
        },
        columnDefs: [
            {
                targets: 0,
                width: '80px',
                className: 'dt-center'
            },
            {
                targets: 2,
                width: '200px',
                orderable: false,
                responsivePriority: 10
            },
            {
                targets: 3,
                width: '80px',
                className: 'dt-center'
            },
            {
                targets: 4,
                width: '120px',
                className: 'dt-center'
            },
            {
                targets: 5,
                width: '80px',
                className: 'dt-center',
                responsivePriority: 5,
                render: function(data, type, row) {
                    if (type === 'display') {
                        return formatHostRating(data);
                    }
                    // For sorting: treat null/empty as -Infinity so they sort last
                    if (type === 'sort') {
                        return data === null || data === '' ? -Infinity : parseFloat(data) || data;
                    }
                    return data;
                }
            },
            {
                targets: 6,
                width: '80px',
                className: 'dt-center',
                responsivePriority: 6,
                render: function(data, type, row) {
                    if (type === 'display') {
                        return formatHostRating(data);
                    }
                    if (type === 'sort') {
                        return data === null || data === '' ? -Infinity : parseFloat(data) || data;
                    }
                    return data;
                }
            },
            {
                targets: 7,
                width: '80px',
                className: 'dt-center',
                responsivePriority: 7,
                render: function(data, type, row) {
                    if (type === 'display') {
                        return formatHostRating(data);
                    }
                    if (type === 'sort') {
                        return data === null || data === '' ? -Infinity : parseFloat(data) || data;
                    }
                    return data;
                }
            },
            {
                targets: 8,
                width: '90px',
                className: 'dt-center',
                responsivePriority: 4,
                render: function(data, type, row) {
                    if (type === 'display') {
                        return formatHostRating(data);
                    }
                    if (type === 'sort') {
                        // For text ratings, they should sort last
                        return data === null || data === '' ? -Infinity : data;
                    }
                    return data;
                }
            },
            {
                targets: 9,
                orderable: false
            },
            {
                targets: 10,
                width: '100px',
                orderable: false,
                className: 'dt-center'
            }
        ]
    });
}

// Render subscription service filters
function renderServiceFilters(services) {
    const container = $('#service-filters');
    container.empty();

    if (!services || services.length === 0) {
        container.append('<span class="service-empty">No subscription services available.</span>');
        $('#clear-service-filters').prop('disabled', true);
        return;
    }

    services.forEach(serviceKey => {
        const label = serviceNames[serviceKey] || formatServiceLabel(serviceKey);
        const inputId = `service-${serviceKey}`;
        const option = `
            <label class="service-option" for="${inputId}">
                <input type="checkbox" id="${inputId}" value="${serviceKey}">
                <span>${label}</span>
            </label>
        `;
        container.append(option);
    });

    $('#clear-service-filters').prop('disabled', false);
}

// Format episode number with link
function formatEpisodeNumber(episodeNum, episodeUrl) {
    if (!episodeNum) {
        return '<span class="no-streaming">-</span>';
    }

    if (episodeUrl) {
        return `<a href="${episodeUrl}" target="_blank" rel="noopener noreferrer" class="episode-link">${episodeNum}</a>`;
    }

    return episodeNum;
}

// Format IMDb rating
function formatRating(rating, votes) {
    if (!rating || rating === 'N/A') {
        return '<span class="no-streaming">No rating</span>';
    }

    const stars = '⭐';
    const formattedVotes = votes && votes !== 'N/A' ? ` (${votes} votes)` : '';

    return `<div class="rating">
        <span class="rating-stars">${stars}</span>
        <strong>${rating}</strong>
        <span class="rating-votes" style="font-size:0.8em; color:#6b7280;">${formattedVotes}</span>
    </div>`;
}

// Format plot with truncation and tooltip
function formatPlot(plot) {
    if (!plot || plot === 'N/A' || plot.trim() === '') {
        return '<span class="no-streaming">-</span>';
    }

    // Truncate long plots
    const maxLength = 100;
    if (plot.length > maxLength) {
        const truncated = plot.substring(0, maxLength - 3) + '...';
        return `<span class="plot-text" title="${plot.replace(/"/g, '&quot;')}">${truncated}</span>`;
    }

    return `<span class="plot-text">${plot}</span>`;
}

// Format host rating (handles both numeric and text)
function formatHostRating(rating) {
    if (!rating || rating === 'N/A' || rating === null) {
        return '<span class="no-streaming">-</span>';
    }

    // Check if numeric for color coding
    const numericRating = parseFloat(rating);
    if (!isNaN(numericRating)) {
        let colorClass = 'rating-low';
        if (numericRating >= 4) {
            colorClass = 'rating-high';
        } else if (numericRating >= 3) {
            colorClass = 'rating-medium';
        }
        return `<span class="host-rating ${colorClass}">${rating}</span>`;
    }

    // Return text rating as-is
    return `<span class="host-rating">${rating}</span>`;
}

// Format streaming options as badges
function formatStreamingOptions(options) {
    if (!options || options.length === 0) {
        return '<span class="no-streaming">Not available</span>';
    }

    const badges = options.map(option => {
        const serviceName = serviceNames[option.service] || option.service;
        const badgeClass = `badge-${option.service}`;
        const typeClass = option.type ? `badge-${option.type}` : '';
        const title = `${serviceName} - ${option.type || 'subscription'}${option.price ? ' - ' + option.price : ''}`;

        let badgeText = serviceName;
        if (option.type === 'rent' || option.type === 'buy') {
            badgeText += option.price ? ` ${option.price}` : ` (${option.type})`;
        }

        const link = option.link || '#';

        return `<a href="${link}" target="_blank" rel="noopener noreferrer"
                   class="streaming-badge ${badgeClass} ${typeClass}"
                   title="${title}">
            ${badgeText}
        </a>`;
    }).join('');

    return `<div class="streaming-badges">${badges}</div>`;
}

// Format IMDb link
function formatLinks(imdbUrl, imdbId) {
    if (!imdbUrl && !imdbId) {
        return '<span class="no-streaming">-</span>';
    }

    const url = imdbUrl || `https://www.imdb.com/title/${imdbId}`;

    return `<div class="movie-links">
        <a href="${url}" target="_blank" rel="noopener noreferrer" class="link-button">
            IMDb
        </a>
    </div>`;
}

// Setup event listeners
function setupEventListeners() {
    registerServiceFilter();

    $('#service-filters').on('change', 'input[type="checkbox"]', function() {
        applyServiceFilters();
    });

    $('#clear-service-filters').on('click', function() {
        $('#service-filters input[type="checkbox"]').prop('checked', false);
        applyServiceFilters();
    });
}

// Apply subscription service filters
function applyServiceFilters() {
    if (!dataTable) return;
    dataTable.draw();
}

function getSelectedServices() {
    return $('#service-filters input[type="checkbox"]:checked')
        .map((_, input) => $(input).val())
        .get();
}

function isSubscriptionOption(option) {
    const optionType = option.type || 'subscription';
    return optionType === 'subscription';
}

function formatServiceLabel(serviceKey) {
    return serviceKey
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function getAvailableSubscriptionServices() {
    const services = new Set();

    moviesData.forEach(movie => {
        (movie.streaming_options || []).forEach(option => {
            if (option.service && isSubscriptionOption(option)) {
                services.add(option.service);
            }
        });
    });

    return Array.from(services).sort((a, b) => {
        const labelA = serviceNames[a] || formatServiceLabel(a);
        const labelB = serviceNames[b] || formatServiceLabel(b);
        return labelA.localeCompare(labelB);
    });
}

function registerServiceFilter() {
    $.fn.dataTable.ext.search.push((settings, data, dataIndex) => {
        if (!dataTable || settings.nTable !== dataTable.table().node()) {
            return true;
        }

        const selectedServices = getSelectedServices();
        if (selectedServices.length === 0) {
            return true;
        }

        const movie = moviesData[dataIndex];
        if (!movie || !movie.streaming_options) {
            return false;
        }

        return movie.streaming_options.some(option =>
            option.service &&
            selectedServices.includes(option.service) &&
            isSubscriptionOption(option)
        );
    });
}
