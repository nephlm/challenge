var verodinApp = angular.module('verodinApp', ['ui.bootstrap']);

verodinApp.controller('VerodinCtrl',
    ['$scope', '$http', '$interval',
    function ($scope, $http, $interval) {
    $scope.regions = [];  // Regions for drop down
    $scope.runningWorkers = {};  // Currently running workers
    $scope.newUrls = '';  // The text box contents
    $scope.work = {};  // The queue.
    $scope.error = '';  // The last error; don't do anything with it yet
    $scope.selectedRegion = ['', ''];  // State of the dropdown.


    // Get the regions; only happens once.
    $http.get('/api/regions').
        success(function(data) {
            $scope.regions = data['result'];
            $scope.selectedRegion = $scope.regions[0];
        }).
        error(function(data) {
            $scope.error = 'Could not retrieve regions';
        });

    // Set state of dropdown
    $scope.setRegion = function(index) {
        $scope.selectedRegion = $scope.regions[index];
    };

    // Issue a start command to a region.
    $scope.startWorker = function() {
        $http.get('/api/start/' + $scope.selectedRegion[0]).
        success(function(data) {
            $scope.runningWorkers = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could not start worker';
        });
    }

    // stop the specified worker
    $scope.stopWorker = function(region, id) {
        $http.get('/api/' + region + '/' + id + '/stop').
        success(function(data) {
            $scope.runningWorkers = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could not stop worker';
        });
    }

    // Get the list of running workers.
    // Run at an interval.
    $scope.getWorkers = function() {
        $http.get('/api/worker').
        success(function(data) {
            $scope.runningWorkers = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could retrieve workers';
        });
    }

    // Get the current state of the queue.
    // Run at an interval.
    $scope.getQueue = function() {
        $http.get('/api/work').
        success(function(data) {
            $scope.work = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could retrieve work';
        });
    }

    // Called to add text box contents to the queue.
    $scope.addUrls = function() {
        $http.post('/api/work',
            {'urls': $scope.newUrls.split('\n')}).
            success(function(data) {
                $scope.newUrls = '';
                $scope.getQueue();
            });
    }


    // Empty the queue.
    $scope.clearQueue = function() {
        $http.delete('/api/work').
        success(function(data) {
            $scope.getQueue()
        }).
        error(function(data) {
            $scope.error = 'Could delete queue';
        });
    }

    // Update the page from the backend.
    // Run at interval.
    $scope.update = function() {
        $scope.getWorkers();
        $scope.getQueue();
    }

    // First update.
    $scope.update()

    // Setup scheduler
    var tick = $interval($scope.update, 5000);

    // Cancel interval on page changes
    // Only one page, so it probably isn't needed.
    $scope.$on('$destroy', function(){
        if (angular.isDefined(tick)) {
            $interval.cancel(tick);
            tick = undefined;
        }
    });



}]);
