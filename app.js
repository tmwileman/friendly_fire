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
    // Prepare table data
    const tableData = moviesData.map(movie => [
        movie.episode_number || '',
        movie.title || '',
        movie.year || '',
        formatRating(movie.imdb_rating, movie.imdb_votes),
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
                width: '80px',
                className: 'dt-center'
            },
            {
                targets: 3,
                width: '120px',
                className: 'dt-center'
            },
            {
                targets: 4,
                orderable: false
            },
            {
                targets: 5,
                width: '100px',
                orderable: false,
                className: 'dt-center'
            }
        ]
    });
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
    // Service filter
    $('#service-filter').on('change', function() {
        const selectedService = $(this).val();
        filterByService(selectedService);
    });
}

// Filter table by streaming service
function filterByService(service) {
    if (!dataTable) return;

    if (!service) {
        // Clear filter
        dataTable.search('').draw();
        return;
    }

    // Search in the "Where to Watch" column (index 4)
    dataTable.column(4).search(serviceNames[service] || service, true, false).draw();
}

// Helper function to get streaming service from movie
function hasStreamingService(movie, service) {
    if (!movie.streaming_options) return false;

    return movie.streaming_options.some(option =>
        option.service.toLowerCase() === service.toLowerCase()
    );
}
