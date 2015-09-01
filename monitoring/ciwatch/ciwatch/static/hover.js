// Code adapted from https://css-tricks.com/row-and-column-highlighting/
$(document).ready(function () {
  $("table").delegate("td.result","mouseover mouseleave", function(e) {
      if (e.type == "mouseover") {
        $(this).parent().addClass("hover");
        $("colgroup").eq($(this).index()).addClass("hover");
      }
      else {
        $(this).parent().removeClass("hover");
        $("colgroup").eq($(this).index()).removeClass("hover");
      }
  });
  $("table").delegate("td.ci-name","mouseover mouseleave", function(e) {
      if (e.type == "mouseover") {
        $(this).parent().addClass("hover");
      }
      else {
        $(this).parent().removeClass("hover");
      }
  });

  $('[data-toggle="popover"]').popover({trigger: 'hover'});
});
