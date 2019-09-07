angular.module('App.Controllers')

// App Controller
.controller('AppController', ['$scope',
  function($scope) {
    $scope.step = 1;
    function _handleError(evt, err) {
      alert('Error: ' + err.process + ' [' + err.statusCode + ', ' + err.error + ']');
    }
    $scope.$on('SERVICE_ERROR', angular.bind(this, _handleError));
  }
])

.controller('PostcodeController', ['$scope',
  function($scope) {
    $scope.step = 2;
    function _handleError(evt, err) {
      alert('Error: ' + err.process + ' [' + err.statusCode + ', ' + err.error + ']');
    }
    $scope.$on('SERVICE_ERROR', angular.bind(this, _handleError));
  }
])

.controller('EbillController', ['$scope',
  function($scope) {
    $scope.step = 31;
    function _handleError(evt, err) {
      alert('Error: ' + err.process + ' [' + err.statusCode + ', ' + err.error + ']');
    }
    $scope.$on('SERVICE_ERROR', angular.bind(this, _handleError));
  }
])

// Store Controller
.controller('StoreController', ['$scope', '$timeout', 'CustomerDataService',
  function($scope, $timeout, CustomerDataService) {

    this.customers = [];
    this.report = '';

    // fetch customers:
    CustomerDataService.getCustomers()
      .success(angular.bind(this, function(data) {
        this.customers = data.customers;
        angular.forEach(this.customers, function(val, key, obj) {
          obj[key].reset = reset.bind(obj[key]);
        }, this);
      }));

    function reset() {
      this.clicks = 0;
      this.selected = false;
    }

    // reset click count on a customer:
    this.resetCustomer = function(idx) {
      this.getCustomer(idx).reset();
    };
    
    this.getCustomer = function(idx) {
      return this.customers[idx];
    };

    // create report summary: 
    this.createReport = function() {
      this.report = '';
      angular.forEach(this.customers, function(item) {
        this.report += item.name + ': Updated ' + item.clicks + ' times<br/>';
      }, this);
    };

    // monitor for changes:
    $scope.$watch(
      angular.bind(this, function() {
        return this.customers;
      }),
      angular.bind(this, this.createReport),
      true
    );
  }
]);