/*
 * Easy Bar Charts
 *
 * https://github.com/patrick-east/EZBC-js
 *
 * This only makes vertical stacked bar charts. The will be the size of
 * whatever container you draw it in. It does not retain data, handle
 * resize, make other types of graphs, deliver beer, or anything special.
 */
var EZBC = (function () {
    var chart = {};
    /*
     * Expect a container element reference and data in the format of:
     *  [
     *      {
     *          value: 50,
     *          color: "#FF00FF",
     *          label: "wins",
     *          border: true,
     *          borderColor: "#000000"
     *      },
     *      {
     *          value: 10,
     *          color: "yellow",
     *          label: "loses"
     *      },
     *  ]
     *
     *  Note: The order of elements is how they will be drawn from bottom to top.
     */
    chart.draw = function (container, data, borderSize, borderColor) {
        var totalValue = 0;
        for (var i = 0; i < data.length; i++) {
            totalValue += data[i]['value'];

            // check for some 'required' fields and try some defaults...
            if (!data[i].hasOwnProperty('color')) {
                data[i].color = '#'+Math.floor(Math.random()*16777215).toString(16);
            }

            if (!data[i].hasOwnProperty('border')) {
                data[i].border = false;
            }
            else if (!data[i].hasOwnProperty('borderColor')) {
                data[i].borderColor = '#000000';
            }
        }

        var chartHeight = parseFloat(container.style.height);
        var chartWidth = parseFloat(container.style.width);

        var chartSVG = '<svg ';
        chartSVG += 'width="' + chartWidth + '" ';
        chartSVG += 'height="' + chartHeight + '" ';
        chartSVG += 'style="border: ' + borderSize + 'px ' + borderColor +  '">';

        // adjust for the border width...
        chartHeight -= borderSize * 2;
        chartWidth -= borderSize * 2;

        var currentY = chartHeight;
        for (var i = 0; i < data.length; i++) {
            if (!data[i].value) {
                continue;  // skip empty ones
            }
            var rectHeight = Math.round(chartHeight * (data[i].value / totalValue));
            chartSVG += '<rect ';
            chartSVG += 'width="' + chartWidth + '" ';
            chartSVG += 'height="' + currentY + '" ';
            chartSVG += 'x=' + borderSize + ' ';
            chartSVG += 'y=' + borderSize + ' ';
            chartSVG += 'style="fill:' + data[i].color + ';';
            if (data[i].border) {
                chartSVG += 'stroke-width:' + borderSize + ';stroke:' + data[i].borderColor + ';';
            }
            chartSVG += '">';
            if (data[i].hasOwnProperty('label')) {
                chartSVG += '<title>' + data[i].label + '</title>';
            }
            chartSVG += '</rect>';
            currentY -= rectHeight;
        }
        chartSVG += '</svg>';
        container.innerHTML = chartSVG;
    };

    return chart;
}());