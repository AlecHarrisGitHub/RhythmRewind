// static/js/charts.js

document.addEventListener('DOMContentLoaded', function() {
    var ctx1 = document.getElementById('popularityChart').getContext('2d');
    var popularityChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: trackNames,
            datasets: [{
                label: 'Popularity Score',
                data: popularityScores,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Popularity Score' }
                },
                x: { title: { display: true, text: 'Track Names' } }
            }
        }
    });

    var ctx2 = document.getElementById('topArtistsChart').getContext('2d');
    var topArtistsChart = new Chart(ctx2, {
        type: 'pie',
        data: {
            labels: artistNames,
            datasets: [{
                label: 'Top Artists',
                data: artistFollowers,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' }
            }
        }
    });

    var ctx3 = document.getElementById('recentlyPlayedChart').getContext('2d');
    var recentlyPlayedChart = new Chart(ctx3, {
        type: 'bar',
        data: {
            labels: recentlyPlayedNames,
            datasets: [{
                label: 'Play Count',
                data: playCounts,
                backgroundColor: 'rgba(153, 102, 255, 0.2)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Play Count' }
                },
                x: { title: { display: true, text: 'Track Names' } }
            }
        }
    });

    var ctx4 = document.getElementById('newMusicChart').getContext('2d');
    var newMusicChart = new Chart(ctx4, {
        type: 'line',
        data: {
            labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
            datasets: [{
                label: 'New Music Discovery',
                data: [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Amount of New Music' }
                },
                x: { title: { display: true, text: 'Month' } }
            }
        }
    });
});
