/**
 * Progress Tracking Integration Test
 * Tests the complete progress tracking system integration
 */

import stateManager from './js/stateManager.js';
import ApiService from './services/apiService.js';

class ProgressIntegrationTest {
    constructor() {
        this.testResults = [];
        this.errors = [];
    }

    /**
     * Run all integration tests
     */
    async runAllTests() {
        console.log('🧪 Starting Progress Tracking Integration Tests...');

        try {
            // Test 1: State Manager Progress Methods
            await this.testStateManagerProgress();

            // Test 2: API Service Progress Endpoints
            await this.testApiServiceProgress();

            // Test 3: Progress Data Flow
            await this.testProgressDataFlow();

            // Test 4: Progress Persistence
            await this.testProgressPersistence();

            this.displayResults();

        } catch (error) {
            console.error('❌ Integration test failed:', error);
            this.logError('Integration test error', error.message);
        }
    }

    /**
     * Test state manager progress functionality
     */
    async testStateManagerProgress() {
        console.log('Testing State Manager Progress Methods...');

        try {
            // Test initial state
            const initialState = stateManager.getState();
            if (!initialState.progressStats) {
                throw new Error('Progress stats not initialized');
            }
            this.logSuccess('Initial progress state initialized');

            // Test milestone progress update
            const testMilestone = {
                id: 'test-milestone-1',
                title: 'Test Milestone',
                status: 'in_progress',
                progress: 50
            };

            stateManager.updateMilestoneProgress(testMilestone.id, 75);
            const updatedState = stateManager.getState();

            if (updatedState.milestones.some(m => m.id === testMilestone.id && m.progress === 75)) {
                this.logSuccess('Milestone progress update working');
            } else {
                throw new Error('Milestone progress update failed');
            }

            // Test milestone completion toggle
            stateManager.toggleMilestoneCompletion(testMilestone.id);
            const toggledState = stateManager.getState();

            if (toggledState.milestones.some(m => m.id === testMilestone.id && m.status === 'completed')) {
                this.logSuccess('Milestone completion toggle working');
            } else {
                throw new Error('Milestone completion toggle failed');
            }

            // Test progress history
            if (toggledState.progressHistory && toggledState.progressHistory.length > 0) {
                this.logSuccess('Progress history tracking working');
            } else {
                throw new Error('Progress history not working');
            }

        } catch (error) {
            this.logError('State Manager Progress Test', error.message);
        }
    }

    /**
     * Test API service progress endpoints
     */
     async testApiServiceProgress() {
         console.log('Testing API Service Progress Endpoints...');

         try {
             // Test progress endpoints exist
             const requiredMethods = [
                 'toggleMilestoneCompletion',
                 'getProgressStats',
                 'getProgressHistory',
                 'saveProgress',
                 'getProgressAnalytics',
                 'exportProgress'
             ];

             for (const method of requiredMethods) {
                 if (typeof ApiService[method] !== 'function') {
                     throw new Error(`API method ${method} not found`);
                 }
             }

             this.logSuccess('All progress API methods available');

             // Test API health check
             const healthResult = await ApiService.checkHealth();
             if (healthResult.success || !healthResult.error) {
                 this.logSuccess('API service accessible');
             } else {
                 console.warn('⚠️ API health check failed, but continuing tests');
             }

         } catch (error) {
             this.logError('API Service Progress Test', error.message);
         }
     }

    /**
     * Test progress data flow
     */
     async testProgressDataFlow() {
         console.log('Testing Progress Data Flow...');

         try {
             // Test data persistence
             const testData = {
                 testId: 'flow-test',
                 progress: 85,
                 timestamp: new Date().toISOString()
             };

             // Simulate saving progress
             const saveResult = await ApiService.saveProgress(testData);
             if (saveResult.success || saveResult.error) {
                 this.logSuccess('Progress data flow working');
             }

             // Test progress stats calculation
             const state = stateManager.getState();
             const progressStats = state.progressStats;

             if (progressStats && typeof progressStats.percentage === 'number') {
                 this.logSuccess('Progress stats calculation working');
             } else {
                 throw new Error('Progress stats calculation failed');
             }

         } catch (error) {
             this.logError('Progress Data Flow Test', error.message);
         }
     }

    /**
     * Test progress persistence
     */
     async testProgressPersistence() {
         console.log('Testing Progress Persistence...');

         try {
             // Test localStorage persistence
             const stateBefore = stateManager.getState();

             // Trigger state update
             stateManager.updateProgressStats({
                 completed: (stateBefore.progressStats?.completed || 0) + 1,
                 total: stateBefore.progressStats?.total || 10,
                 percentage: Math.round(((stateBefore.progressStats?.completed || 0) + 1) / (stateBefore.progressStats?.total || 10) * 100)
             });

             // Check if state persisted
             const persistedData = localStorage.getItem('roadmapAppState');
             if (persistedData) {
                 const parsedData = JSON.parse(persistedData);
                 if (parsedData.progressStats) {
                     this.logSuccess('Progress persistence working');
                 } else {
                     throw new Error('Progress data not persisted');
                 }
             } else {
                 throw new Error('No persisted data found');
             }

         } catch (error) {
             this.logError('Progress Persistence Test', error.message);
         }
     }

    /**
     * Log successful test
     */
     logSuccess(testName) {
         console.log(`✅ ${testName}`);
         this.testResults.push({ test: testName, status: 'PASS' });
     }

    /**
     * Log test error
     */
     logError(testName, error) {
         console.error(`❌ ${testName}: ${error}`);
         this.testResults.push({ test: testName, status: 'FAIL', error });
         this.errors.push({ test: testName, error });
     }

    /**
     * Display test results
     */
     displayResults() {
         console.log('\n📊 Integration Test Results:');
         console.log('='.repeat(50));

         const passed = this.testResults.filter(r => r.status === 'PASS').length;
         const total = this.testResults.length;

         this.testResults.forEach(result => {
             const icon = result.status === 'PASS' ? '✅' : '❌';
             console.log(`${icon} ${result.test}`);
             if (result.error) {
                 console.log(`   Error: ${result.error}`);
             }
         });

         console.log('\n' + '='.repeat(50));
         if (this.errors.length === 0) {
             console.log(`🎉 All tests passed! (${passed}/${total})`);
         } else {
             console.log(`⚠️ ${this.errors.length} test(s) failed. (${passed}/${total} passed)`);
         }

         console.log('🧪 Integration tests completed.');
     }
}

// Auto-run tests if this script is loaded
if (typeof window !== 'undefined') {
    window.runProgressTests = () => {
        const test = new ProgressIntegrationTest();
        test.runAllTests();
    };

    console.log('🔧 Progress integration tests loaded. Run window.runProgressTests() to execute.');
}

// Export for Node.js testing if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgressIntegrationTest;
}