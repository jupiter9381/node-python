angular.module('App.Services')
  .service('CustomerDataService', ['$http', '$rootScope',
    function($http, $rootScope) {

      // notify app about service error:
      function reportError(process, err) {
        err.process = process;
        $rootScope.$broadcast('SERVICE_ERROR', err);
      }

      // mock service to return dummy data:
      this.getCustomers = function() {
        var request = $http.get('customer-data.json');
        request.error(function(err) {
          reportError('getCustomers', err);
        });
 
        return request;
      };
 
      // service identifier:
      this.toString = function() {
        return 'CustomerDataService';
      };

    }
  ]);