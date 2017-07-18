/**
 * Created by harkous on 30.11.16.
 */
(function(){
    'use strict';

    angular.module('app')
        .service('recommenderService', [
            '$q',
            '$http',
            recommender
        ]);

    function recommender($q,$http){
        return {
            query: function(latitude, longitude, age) {
                var apiUrl = 'http://lsirpc32.epfl.ch:5001/query?latitude='+latitude+'&longitude='+longitude+'&age='+age;
                return $http({
                    url: apiUrl
                });
            }
        }
    }
})();
