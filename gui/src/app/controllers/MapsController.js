(function () {
    angular
        .module('app')
        .controller('MapsController', [
            "$scope",
            'recommenderService',
            'leafletData',
            '$timeout',
            GoogleMapsController
        ]);
    function GoogleMapsController($scope, recommenderService, leafletData, $timeout) {
        var self = this;

        function toTitleCase(str) {
            return str.replace(/\w\S*/g, function (txt) {
                return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
            });
        }

        // initial values for data
        $scope.age = {val: 20};

        $scope.user = {
            lat: 51.515366,
            lng: -0.1109577,
            zoom: 10
        };
        var leafIcon = {
            iconUrl: 'assets/images/green_home.png',
            iconSize: [37.5, 60], // size of the icon
            popupAnchor: [0, -15] // point from which the popup should open relative to the iconAnchor
        };

        // center message for the user location
        function getCenterMessage() {
            return '<div layout="row" class="layout-row"><div flex="33" class="flex-33">    <img class="responsive-img" height="50px" src="assets/images/0.png"></div><div flex="66" style="font-size: large" class="flex-66">I\'m <strong>you</strong>, and you told me I\'m <strong>' + $scope.age.val + '</strong> years old.<br>' +
                '<span style="font-size: medium">P.S: Drag me around! <img class="responsive-img" height="15" src="assets/images/wink.svg"> </span></div></div>';
        }

        $scope.centerMessage = getCenterMessage();
        $scope.markers = [];


        $scope.centerMarker = {

            lat: $scope.user.lat,
            lng: $scope.user.lng,
            message: $scope.centerMessage,
            focus: true,
            icon: leafIcon,
            draggable: true

        };
        $scope.markers = [$scope.centerMarker];

        // paramters to prevent multiple bound fits
        $scope.lastBounding = 0;
        var delay = 500;
        // fit the bound to the markers
        $scope.fitBounds = function () {
            if ($scope.lastBounding >= (Date.now() - delay)) {
                return;
            }
            $scope.lastBounding= Date.now();
            console.log('fitting bounds')
            leafletData.getMap().then(function (map) {
                map.fitBounds($scope.bounds);
                $timeout(function () {
                    map.invalidateSize();
                });
            });
        };

        // event when the leaflet is dragged
        $scope.$on('leafletDirectiveMarker.dragend', function (e, args) {
            $scope.user.lng = args.model.lng;
            $scope.user.lat = args.model.lat;
            $scope.latChange();
            $scope.lngChange();
            $scope.fetchRecommendations()
        });



        angular.extend($scope, {


            fetchRecommendations: function () {
                // function to fetch the recommendations from the server
                recommenderService
                    .query($scope.user.lat, $scope.user.lng, $scope.age.val)
                    .then(function (response) {
                        $scope.markers = $scope.markers.slice(0, 1);
                        self.neighborsData = response.data.result;
                        $scope.bounds = [[$scope.user.lat, $scope.user.lng]];
                        for (var i = 0; i < self.neighborsData.length; i++) {
                            var item = self.neighborsData[i];
                            var longitude = item.longitude;
                            var latitude = item.latitude;
                            var name = item.name.replace(',', ' ');
                            var age = item.age;

                            $scope.bounds.push([latitude, longitude]);
                            $scope.markers.push({
                                lat: latitude,
                                lng: longitude,
                                message: '<div layout="row" class="layout-row"><div flex="33" class="flex-33">    <img class="responsive-img" height="50px" src="assets/images/' + (i + 1) + '.png"></div><div flex="66" style="font-size: large" class="flex-66">I\'m <strong>' + toTitleCase(name) + '</strong>, and I\'m <strong>' + age + '</strong> years old.</div></div>'
                            });
                        }


                        $scope.fitBounds()
                    })
            }

        });

        $scope.fetchRecommendations();

        // triggered when the age changes
        $scope.ageChange = function () {
            console.log('age changed');
            $scope.centerMessage = getCenterMessage();
            $scope.markers[0].message = $scope.centerMessage;
            $scope.fetchRecommendations();

        };

        // triggered when the latitude changes
        $scope.latChange = function () {
            console.log('latitude changed');
            $scope.markers[0].lat = $scope.user.lat;
            $scope.fetchRecommendations();
        };

        // triggered when the longitude changes
        $scope.lngChange = function () {
            console.log('longitude changed');
            $scope.markers[0].lng = $scope.user.lng;
            $scope.fetchRecommendations();
        };


    }
})();
