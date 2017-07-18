(function(){
  'use strict';

  angular.module('app', [ 'ngMaterial','leaflet-directive']);
  angular.module('app').config(function($logProvider){
    $logProvider.debugEnabled(false);
  });

})();

