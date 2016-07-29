var verodinApp = angular.module('verodinApp', ['ui.bootstrap']);

verodinApp.controller('VerodinCtrl',
    ['$scope', '$http', '$interval',
    function ($scope, $http, $interval) {
    $scope.regions = [];
    $scope.error = '';
    $scope.selectedRegion = ['', ''];
    $scope.runningWorkers = {};
    $scope.newUrls = 'Add Urls.  One per line.';

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
        console.log('startWorker');
        $http.get('/api/start/' + $scope.selectedRegion[0]).
        success(function(data) {
            $scope.runningWorkers = data['result'];
        }).
        error(function(data) {
            $scope.error = 'Could not start worker';
        });
    }

    $scope.stopWorker = function(region, id) {
        console.log('startWorker');
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

    $scope.getWorkers()

    var tick = $interval($scope.getWorkers, 5000);

    // Cancel interval on page changes
    $scope.$on('$destroy', function(){
        if (angular.isDefined(tick)) {
            $interval.cancel(tick);
            tick = undefined;
        }
    });

    $scope.addUrls = function() {
        console.log('startWorker');
        $http.post('/api/work/add',
            {'urls': $scope.newUrls.split('\n')}).
            success(function(data) {
                console.log('success');
            });

    }


}]);
