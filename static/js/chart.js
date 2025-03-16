document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts if required elements exist
    if (document.getElementById('programmingChart')) {
        initProgrammingChart();
    }
    
    if (document.getElementById('labUsageChart')) {
        initLabUsageChart();
    }
});

// Programming Languages Chart
function initProgrammingChart() {
    const chartCanvas = document.getElementById('programmingChart');
    
    // Get data from data attributes
    const labelsElement = document.getElementById('prog-labels');
    const countsElement = document.getElementById('prog-counts');
    
    if (!labelsElement || !countsElement) {
        console.error('Chart data elements not found');
        return;
    }
    
    try {
        const labels = JSON.parse(labelsElement.textContent);
        const counts = JSON.parse(countsElement.textContent);
        
        // Color palette
        const colors = [
            '#3366CC', '#DC3912', '#FF9900', '#109618', '#990099',
            '#0099C6', '#DD4477', '#66AA00', '#B82E2E', '#316395'
        ];
        
        // Create chart
        new Chart(chartCanvas, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: colors.slice(0, labels.length),
                    borderColor: 'white',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Programming Languages Distribution'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error initializing programming chart:', error);
    }
}

// Laboratory Usage Chart
function initLabUsageChart() {
    const chartCanvas = document.getElementById('labUsageChart');
    
    // Get data from data attributes
    const labelsElement = document.getElementById('lab-labels');
    const countsElement = document.getElementById('lab-counts');
    
    if (!labelsElement || !countsElement) {
        console.error('Chart data elements not found');
        return;
    }
    
    try {
        const labels = JSON.parse(labelsElement.textContent);
        const counts = JSON.parse(countsElement.textContent);
        
        // Color palette
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#C9CBCF', '#7CFC00', '#FFCC99', '#FFB6C1'
        ];
        
        // Create chart
        new Chart(chartCanvas, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: colors.slice(0, labels.length),
                    borderColor: 'white',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Laboratory Usage Distribution'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error initializing lab usage chart:', error);
    }
}

// Function to create statistical charts for dashboard
function createDashboardCharts(programmingLabels, programmingCounts) {
    if (!programmingLabels || !programmingCounts) {
        console.error('Dashboard chart data not provided');
        return;
    }
    
    const dashboardChartCanvas = document.getElementById('dashboardChart');
    if (!dashboardChartCanvas) {
        console.error('Dashboard chart canvas not found');
        return;
    }
    
    try {
        // Color palette
        const colors = [
            '#3366CC', '#DC3912', '#FF9900', '#109618', '#990099',
            '#0099C6', '#DD4477', '#66AA00', '#B82E2E', '#316395'
        ];
        
        // Create chart
        new Chart(dashboardChartCanvas, {
            type: 'pie',
            data: {
                labels: programmingLabels,
                datasets: [{
                    data: programmingCounts,
                    backgroundColor: colors.slice(0, programmingLabels.length),
                    borderColor: 'white',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Programming Languages Distribution'
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating dashboard chart:', error);
    }
}

// Function to create timeseries charts
function createTimeseriesChart(elementId, labels, datasets, title) {
    const chartCanvas = document.getElementById(elementId);
    if (!chartCanvas) {
        console.error(`Canvas element ${elementId} not found`);
        return;
    }
    
    try {
        new Chart(chartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: title
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Count'
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error(`Error creating ${title} chart:`, error);
    }
}
