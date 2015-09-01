/* Copyright (c) 2015 Tintri. All rights reserved.
 *
 *    Licensed under the Apache License, Version 2.0 (the "License"); you may
 *    not use this file except in compliance with the License. You may obtain
 *    a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *    License for the specific language governing permissions and limitations
 *    under the License.
 */

var toggle1 = function () {
  $(".verified-1").css("background-color", "#FAA");
  $(this).one("click", toggle2);
}

var toggle2 = function () {
  $(".verified-1").css("background-color", "");
  $(this).one("click", toggle1);
}

$(document).ready(function () {
  $("colgroup").each(function (i, elem) {
    if ($(elem).hasClass("verified-1")) {
      $("#results").find("td").filter(":nth-child(" + (i + 1) + ")").addClass("verified-1");
    }
  });
  $("#verified-1-button").one("click", toggle1);
});
