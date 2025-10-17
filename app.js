/**
 * Main Application Module
 * Coordinates all components and manages the overall application state
 */

import ApiService from './services/apiService.js';
import stateManager from './js/stateManager.js';
import UIUtils from './js/uiUtils.js';
import RoadmapVisualizer from './js/roadmapVisualizer.js';
import router from './js/router.js';
import ActivityFeed from './components/ActivityFeed.js';
import ProgressCard from './components/ProgressCard.js';

class RoadmapApp {
    constructor() {
        this.roadmapVisualizer = null;
        this.activityFeed = null;
        this.progressCard = null;
        this.isInitialized = false;

        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            UIUtils.setPageLoading(true);

            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.setup());
            } else {
                this.setup();
            }
        } catch (error) {
            console.error('Failed to initialize app:', error);
            UIUtils.showToast('Failed to initialize application', 'error');
        } finally {
            UIUtils.setPageLoading(false);
        }
    }

    /**
     * Setup application components and event listeners
     */
    setup() {
        this.setupComponents();
        this.setupEventListeners();
        this.setupNavigation();
        this.setupThemeToggle();
        this.loadInitialData();

        this.isInitialized = true;
        console.log('🚀 Roadmap App initialized successfully');
    }

    /**
     * Initialize all components
     */
    setupComponents() {
        // Initialize roadmap visualizer
        this.roadmapVisualizer = new RoadmapVisualizer('roadmap-container');

        // Initialize activity feed
        this.activityFeed = new ActivityFeed('activity-feed');

        // Initialize progress card
        this.progressCard = new ProgressCard('progress-container');

        // Setup window resize handler for roadmap
        window.addEventListener('resize', UIUtils.debounce(() => {
            if (this.roadmapVisualizer) {
                this.roadmapVisualizer.handleResize();
            }
        }, 250));
    }

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Listen for state changes
        stateManager.subscribe((state) => {
            this.handleStateChange(state);
        });

        // Listen for milestone selection
        window.addEventListener('milestone:selected', (event) => {
            this.handleMilestoneSelection(event.detail.milestone);
        });

        // Setup zoom controls
        const zoomInBtn = document.getElementById('zoom-in');
        const zoomOutBtn = document.getElementById('zoom-out');

        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => {
                if (this.roadmapVisualizer) {
                    this.roadmapVisualizer.zoomIn();
                }
            });
        }

        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => {
                if (this.roadmapVisualizer) {
                    this.roadmapVisualizer.zoomOut();
                }
            });
        }
    }

    /**
     * Setup navigation between views
     */
    setupNavigation() {
        const navButtons = document.querySelectorAll('.nav-tab');

        navButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();

                const route = button.dataset.route;
                if (route) {
                    // Use router for navigation
                    window.dispatchEvent(new CustomEvent('route:navigate', {
                        detail: { route: `/${route}` }
                    }));
                } else {
                    // Fallback to old system for backward compatibility
                    const viewId = button.id.replace('nav-', '') + '-view';
                    this.switchView(viewId);
                }

                // Update active state
                navButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
            });
        });

        // Setup user menu dropdowns
        this.setupUserMenus();
    }

    /**
     * Setup theme toggle functionality
     */
    setupThemeToggle() {
        const themeToggles = document.querySelectorAll('#theme-toggle, #theme-toggle-2');

        themeToggles.forEach(toggle => {
            toggle.addEventListener('click', () => {
                stateManager.toggleTheme();
            });
        });
    }

    /**
     * Load initial data
     */
    async loadInitialData() {
        try {
            // Check API health
            await this.checkApiHealth();

            // Load user data if authenticated
            if (stateManager.isLoggedIn()) {
                await this.loadUserData();
            }

            // Load sample roadmap data for demo
            this.loadSampleData();

        } catch (error) {
            console.error('Failed to load initial data:', error);
            UIUtils.showToast('Failed to load initial data', 'error');
        }
    }

    /**
     * Check API health
     */
    async checkApiHealth() {
        const result = await ApiService.checkHealth();

        if (result.success) {
            console.log('✅ API is healthy');
        } else {
            console.warn('⚠️ API health check failed:', result.error);
            UIUtils.showToast('API connection issue', 'warning');
        }
    }

    /**
     * Load user data
     */
    async loadUserData() {
        const result = await ApiService.getUserData();

        if (result.success) {
            stateManager.login(result.data);
        } else {
            console.error('Failed to load user data:', result.error);
        }
    }

    /**
     * Load sample roadmap data for demonstration
     */
    loadSampleData() {
        const sampleRoadmap = {
            id: 'sample-roadmap',
            title: 'Full Stack Development',
            description: 'Complete learning path for full stack development',
            milestones: [
                {
                    id: '1',
                    title: 'HTML & CSS Basics',
                    description: 'Learn fundamental web technologies',
                    status: 'completed',
                    progress: 100
                },
                {
                    id: '2',
                    title: 'JavaScript Fundamentals',
                    description: 'Master JavaScript programming',
                    status: 'completed',
                    progress: 100
                },
                {
                    id: '3',
                    title: 'React Framework',
                    description: 'Build modern user interfaces',
                    status: 'in_progress',
                    progress: 60
                },
                {
                    id: '4',
                    title: 'Node.js Backend',
                    description: 'Create server-side applications',
                    status: 'locked',
                    progress: 0
                },
                {
                    id: '5',
                    title: 'Database Design',
                    description: 'Work with databases',
                    status: 'locked',
                    progress: 0
                },
                {
                    id: '6',
                    title: 'Deployment & DevOps',
                    description: 'Deploy applications to production',
                    status: 'locked',
                    progress: 0
                }
            ]
        };

        stateManager.setCurrentRoadmap(sampleRoadmap);
        stateManager.setMilestones(sampleRoadmap.milestones);

        // Update progress stats
        const completed = sampleRoadmap.milestones.filter(m => m.status === 'completed').length;
        const total = sampleRoadmap.milestones.length;
        stateManager.updateProgressStats({
            completed,
            total,
            percentage: Math.round((completed / total) * 100)
        });

        // Load sample activities
        const sampleActivities = [
            {
                id: '1',
                title: 'Completed milestone: "JavaScript Fundamentals"',
                status: 'completed',
                timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
                badge: 'completed'
            },
            {
                id: '2',
                title: 'Started new roadmap: "Full Stack Development"',
                status: 'info',
                timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
                badge: 'new'
            },
            {
                id: '3',
                title: 'Updated progress on React Framework',
                status: 'in_progress',
                timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
                badge: 'update'
            }
        ];

        this.activityFeed.setActivities(sampleActivities);
    }

    /**
     * Setup user menu dropdowns
     */
    setupUserMenus() {
        // Guest menu dropdown
        const guestMenuBtn = document.getElementById('guest-menu-btn');
        const guestMenuDropdown = document.getElementById('guest-menu-dropdown');

        if (guestMenuBtn && guestMenuDropdown) {
            guestMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                guestMenuDropdown.classList.toggle('hidden');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', () => {
                guestMenuDropdown.classList.add('hidden');
            });
        }

        // Authenticated user menu dropdown
        const userMenuBtn = document.getElementById('user-menu-btn');
        const userMenuDropdown = document.getElementById('user-menu-dropdown');

        if (userMenuBtn && userMenuDropdown) {
            userMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                userMenuDropdown.classList.toggle('hidden');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', () => {
                userMenuDropdown.classList.add('hidden');
            });
        }

        // Logout functionality
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                stateManager.logout();
                window.dispatchEvent(new CustomEvent('route:navigate', {
                    detail: { route: '/' }
                }));
            });
        }
    }

    /**
     * Handle state changes
     */
    handleStateChange(state) {
        // Update current view if not using router
        if (!router.isInitialized) {
            this.updateCurrentView(state.currentView);
        }

        // Update roadmap visualization if roadmap data changed
        if (state.currentRoadmap && this.roadmapVisualizer) {
            this.roadmapVisualizer.render(state.currentRoadmap);
        }

        // Update progress card if stats changed
        if (this.progressCard) {
            this.progressCard.updateStats(state.progressStats);
        }

        // Update navigation based on authentication state
        this.updateNavigationState(state);
    }

    /**
     * Update navigation state based on authentication
     */
    updateNavigationState(state) {
        const authNavItems = document.querySelectorAll('.auth-nav-item');
        const guestNavItems = document.querySelectorAll('.guest-nav-item');

        if (state.isAuthenticated) {
            // Show authenticated navigation
            authNavItems.forEach(item => {
                item.classList.remove('hidden');

                // Show admin nav if user is admin
                if (item.id === 'nav-admin' && state.currentUser?.role === 'admin') {
                    item.classList.remove('hidden');
                } else if (item.id === 'nav-admin' && state.currentUser?.role !== 'admin') {
                    item.classList.add('hidden');
                }
            });
            guestNavItems.forEach(item => item.classList.add('hidden'));
        } else {
            // Show guest navigation
            authNavItems.forEach(item => item.classList.add('hidden'));
            guestNavItems.forEach(item => item.classList.remove('hidden'));
        }
    }

    /**
     * Switch to different view (legacy support)
     */
    switchView(viewId) {
        // If router is available, use it instead
        if (router && router.isInitialized) {
            const routeMap = {
                'dashboard-view': '/dashboard',
                'roadmap-view': '/roadmap',
                'profile-view': '/profile'
            };

            const route = routeMap[viewId];
            if (route) {
                window.dispatchEvent(new CustomEvent('route:navigate', {
                    detail: { route }
                }));
                return;
            }
        }

        // Fallback to old system
        const views = document.querySelectorAll('.view');
        views.forEach(view => view.classList.add('hidden'));

        const targetView = document.getElementById(viewId);
        if (targetView) {
            targetView.classList.remove('hidden');
            stateManager.setCurrentView(viewId.replace('-view', ''));
        }
    }

    /**
     * Update current view based on state (legacy support)
     */
    updateCurrentView(view) {
        if (router && router.isInitialized) {
            const routeMap = {
                'dashboard': '/dashboard',
                'roadmap': '/roadmap',
                'profile': '/profile'
            };

            const route = routeMap[view];
            if (route) {
                window.dispatchEvent(new CustomEvent('route:navigate', {
                    detail: { route }
                }));
            }
        } else {
            this.switchView(`${view}-view`);
        }
    }

    /**
     * Handle milestone selection
     */
    handleMilestoneSelection(milestone) {
        UIUtils.showToast(`Selected: ${milestone.title}`, 'info');

        // Here you could open a modal, navigate to detail view, etc.
        console.log('Milestone selected:', milestone);
    }

    /**
     * Handle quick actions
     */
    setupQuickActions() {
        const startRoadmapBtn = document.getElementById('start-roadmap');
        const createMilestoneBtn = document.getElementById('create-milestone');
        const viewAnalyticsBtn = document.getElementById('view-analytics');
        const exportDataBtn = document.getElementById('export-data');

        if (startRoadmapBtn) {
            startRoadmapBtn.addEventListener('click', () => {
                this.switchView('roadmap-view');
                document.getElementById('nav-roadmap')?.click();
            });
        }

        if (createMilestoneBtn) {
            createMilestoneBtn.addEventListener('click', () => {
                this.showCreateMilestoneModal();
            });
        }

        if (viewAnalyticsBtn) {
            viewAnalyticsBtn.addEventListener('click', () => {
                UIUtils.showToast('Analytics view coming soon!', 'info');
            });
        }

        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', () => {
                this.exportProgressData();
            });
        }
    }

    /**
     * Show create milestone modal
     */
    showCreateMilestoneModal() {
        // Simple prompt for demo - in real app would be a proper modal
        const title = prompt('Enter milestone title:');
        if (title) {
            const description = prompt('Enter milestone description:');
            this.createMilestone(title, description);
        }
    }

    /**
     * Create new milestone
     */
    async createMilestone(title, description) {
        const milestoneData = {
            title,
            description,
            status: 'locked',
            progress: 0,
            roadmapId: stateManager.getState().currentRoadmap?.id
        };

        UIUtils.showToast('Creating milestone...', 'info');

        const result = await ApiService.createMilestone(milestoneData);

        if (result.success) {
            stateManager.addMilestone(result.data);
            UIUtils.showToast('Milestone created successfully!', 'success');

            // Add to activity feed
            this.activityFeed.addActivity({
                id: Date.now().toString(),
                title: `Created new milestone: "${title}"`,
                status: 'info',
                timestamp: new Date(),
                badge: 'new'
            });
        } else {
            UIUtils.showToast('Failed to create milestone', 'error');
        }
    }

    /**
     * Export progress data
     */
    exportProgressData() {
        const state = stateManager.getState();
        const exportData = {
            user: state.currentUser,
            progress: state.progressStats,
            milestones: state.milestones,
            exportDate: new Date().toISOString()
        };

        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });

        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `roadmap-progress-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        UIUtils.showToast('Progress data exported!', 'success');
    }
}

// Initialize the application
const app = new RoadmapApp();

// Make app globally available for debugging
window.RoadmapApp = app;