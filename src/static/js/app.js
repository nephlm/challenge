var verodinApp = angular.module('verodinApp', ['ui.bootstrap']);

verodinApp.controller('VerodinCtrl',
    ['$scope', '$http', '$interval',
    function ($scope, $http, $interval) {
    $scope.regions = [];
    $scope.error = '';
    $scope.selectedRegion = ['', ''];
    $scope.runningWorkers = {};
    $scope.newUrls = '';
    $scope.work = {};

    $http.get('/api/regions').
        success(function(data) {
            $scope.regions = data['result'];
            $scope.selectedRegion = $scope.regions[0];
        }).
        error(function(data) {
            $scope.error = 'Could not retrieve regions';
        });

    $scope.setRegion = function(index) {
        $scope.selectedRegion = $scope.regions[index];
    };

    $scope.startWorker = function() {
        $http.get('/api/start/' + $scope.selectedRegion[0]).
        success(function(data) {
            $scope.runningWorkers = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could not start worker';
        });
    }

    $scope.stopWorker = function(region, id) {
        $http.get('/api/' + region + '/' + id + '/stop').
        success(function(data) {
            $scope.runningWorkers = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could not stop worker';
        });
    }

    $scope.getWorkers = function() {
        $http.get('/api/worker').
        success(function(data) {
            $scope.runningWorkers = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could retrieve workers';
        });
    }

    $scope.getQueue = function() {
        $http.get('/api/work').
        success(function(data) {
            $scope.work = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could retrieve work';
        });
    }

    $scope.addUrls = function() {
        $http.post('/api/work',
            {'urls': $scope.newUrls.split('\n')}).
            success(function(data) {
                $scope.newUrls = '';
                $scope.getQueue();
            });

    }

    $scope.clearQueue = function() {
        $http.delete('/api/work').
        success(function(data) {
            $scope.getQueue()
        }).
        error(function(data) {
            $scope.error = 'Could delete queue';
        });
    }

    $scope.update = function() {
        $scope.getWorkers();
        $scope.getQueue();
    }

    $scope.update()

    var tick = $interval($scope.update, 5000);

    // Cancel interval on page changes
    $scope.$on('$destroy', function(){
        if (angular.isDefined(tick)) {
            $interval.cancel(tick);
            tick = undefined;
        }
    });



}]);
