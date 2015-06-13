
var Scoreboard = (function () {
    var board = {};

    var table_div_id = null;
    var table = null;
    var table_header = null;
    var hostname = null;

    var ci_results = null;
    var ci_accounts = null;
    var user_filter = null;

    var row_cache = {};

    var spinner = null;
    var overlay = null;
    var opaque_overlay = null;

    var hide_overlay = function () {
        spinner.stop();
        overlay.remove();
        opaque_overlay.remove();
    }

    var show_overlay = function () {
        overlay = $(document.createElement('div'));
        overlay.addClass('overlay_clear');
        overlay.appendTo(document.body);
        opaque_overlay = $(document.createElement('div'));
        opaque_overlay.addClass('overlay_opaque');
        opaque_overlay.appendTo(document.body);
        title = $(document.createElement('div'));
        title.addClass('overlay_title');
        title.html('Building results...');
        title.appendTo(overlay);

        var opts = {
            lines: 20, // The number of lines to draw
            length: 35, // The length of each line
            width: 10, // The line thickness
            radius: 45, // The radius of the inner circle
            corners: 1, // Corner roundness (0..1)
            rotate: 0, // The rotation offset
            direction: 1, // 1: clockwise, -1: counterclockwise
            color: '#000', // #rgb or #rrggbb or array of colors
            speed: 1, // Rounds per second
            trail: 60, // Afterglow percentage
            shadow: true, // Whether to render a shadow
            hwaccel: true, // Whether to use hardware acceleration
            className: 'spinner', // The CSS class to assign to the spinner
            zIndex: 2e9, // The z-index (defaults to 2000000000)
            top: '50%', // Top position relative to parent
            left: '50%' // Left position relative to parent
        };
        spinner = new Spinner(opts).spin();
        $(spinner.el).appendTo(overlay);

    }

    var gather_data_and_build = function () {
        show_overlay();
        $.ajax({
            type: 'get',
            url: 'results',
            data: window.location.search.substring(1),
            success: function(data) {
                ci_results = JSON.parse(data);
                get_ci_accounts()
            }
        });
    };

    var get_ci_accounts = function () {
        $.ajax({
            type: 'get',
            url: 'ci-accounts',
            success: function(data) {
                parse_accounts(data);
                build_table();
            }
        });
    }

    var find_ci_in_list = function (ci, list) {
        for (var i = 0; i < list.length; i++) {
            if (ci == list[i]._id) {
                return list[i];
            }
        }
    }

    var parse_accounts = function (ci_accounts_raw) {
        var all_ci_accounts = JSON.parse(ci_accounts_raw);
        var ci_account_objs = {};
        ci_accounts = [];

        // Filter if there is a user url param
        var user_param = get_param_by_name('user')
        user_filter = []
        if (user_param != '') {
            user_filter = user_param.replace(/\s+/g, '').split(',')
        }

        for (var patchset in ci_results) {
            for (var ci in ci_results[patchset].results) {
                if (user_filter.length > 0 && user_filter.indexOf(ci) == -1) {
                    continue;
                }

                if (!(ci in ci_account_objs)) {
                    ci_account_objs[ci] = true;
                    ci_accounts.push(find_ci_in_list(ci, all_ci_accounts));
                }
            }
        }
    }

    var ci_account_header = function (user_name, user_name_pretty) {
        return user_name_pretty + ' <br /> (' + user_name + ')';
    };

    var create_header = function () {
        td = $(document.createElement('td'));
        td.addClass('pretty_table_header');
        return td;
    };

    var create_filler = function (td) {
        if (!td) td = $(document.createElement('td'));
        td.addClass('no_result');
        td.html('&nbsp');
        return td;
    };

    var add_header = function (header_title) {
        var td = create_header();
        td.html(header_title);
        td.appendTo(table_header);
    };

    var set_result = function(cell, result) {
        var cell_class = null;

        switch (result) {
            case 'SUCCESS':
                cell_class = 'success';
                break;
            case 'FAILURE':
            case 'ERROR':
            case 'NOT_REGISTERED':
            case 'ABORTED':
                cell_class = 'fail';
                break;
            case 'MERGE FAILED':
            case 'UNKNOWN':
            default:
                cell_class = 'unknown';
                break;
        }

        cell.removeClass().addClass(cell_class);
        cell.html(result);
    };

    var add_on_click_url = function(element, url) {
        element.on('click', (function () {
            // closures are weird.. scope the url so each on click is using
            // the right one and not just the last url handled by the loop
            var review_url = url;
            return function () {
                window.open(review_url, '_blank');
            }
        })());
    };

    var handle_patchset = function(patchset) {
        var result_row = null;
        var ci_index = null;
        // console.log(JSON.stringify(result));
        var review_id_patchset = patchset._id;

        // add a new row for the review number + patchset
        result_row = $(document.createElement('tr'));
        result_row.appendTo(table);
        var label = create_header();
        label.html(review_id_patchset);
        label.appendTo(result_row);
        var review_patchset_split = review_id_patchset.split(',');
        var url = "https://review.openstack.org/#/c/" + review_patchset_split[0] + "/" + review_patchset_split[1];
        add_on_click_url(label, url);
        label.prop('title', url);

        for (var i = 0; i < ci_accounts.length; i++) {
            var ci_account = ci_accounts[i];
            var td = $(document.createElement('td'));
            if (ci_account._id in patchset.results) {
                var result = patchset.results[ci_account._id];
                add_on_click_url(td, url)
                td.prop('title', url);
                set_result(td, result);
            }
            else {
                td = create_filler(td);
            }
            td.appendTo(result_row);
        }
    }

    var build_table = function () {
        table = $(document.createElement('table'));
        table.addClass('pretty_table');
        table.attr('cellspacing', 0);
        table_container = $('#' + table_div_id);
        table_container.addClass('scoreboard_container');
        table.appendTo(table_container);

        // build a table header that will (by the time
        // we're done) have row for each ci account name
        table_header = $(document.createElement('tr'));
        create_header().appendTo(table_header); // spacer box
        table_header.appendTo(table);

        for (var i = 0; i < ci_accounts.length; i++) {
            var ci = ci_accounts[i]
            add_header(ci_account_header(ci._id, ci.user_name_pretty));
        }

        // TODO: maybe process some of this in a worker thread?
        // It might be nice if we can build a model and then render it
        // all in one go instead of modifying the DOM so much...
        //
        // For now we will handle a single result at a time (later on
        // we could maybe stream/pull incremental updates so the page
        // is 'live').
        //
        // This will add each result into the table and then yield
        // the main thread so the browser can render, handle events,
        // and generally not lock up and be angry with us. It still
        // takes a while to actually build out the table, but at least
        // it will be more exciting to watch all the results pop up
        // on the screen instead of just blank page.
        var index = 0;
        var num_results = ci_results.length;
        (function handle_patchset_wrapper() {
            if (index < num_results) {
                handle_patchset(ci_results[index]);
                index++;
                window.setTimeout(handle_patchset_wrapper, 0);
            } else {
                hide_overlay();
            }
        })();
    };

    var add_input_to_form = function (form, input_type, label_text, input_name, starting_val) {
        var label = $('<label>').text(label_text + ":");
        var input = $('<input/>').attr({type: input_type, id: input_name, name: input_name});
        input.appendTo(label);
        if (starting_val) {
            input.val(starting_val);
        }
        label.appendTo(form);
        return input;
    }

    var add_break_to_form = function (form) {
        $('<br/>').appendTo(form);
    }

    var get_param_by_name = function (name) {
        name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
        var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
            results = regex.exec(window.location.search);
        return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
    }

    board.show_query_box = function (host, container) {
        var qb_container = $('#' + container);
        qb_container.addClass('query_box_container');

        // create a div inside the container to hold the form stuff
        qb_div = $(document.createElement('div'));
        qb_div.addClass('query_box');
        qb_div.appendTo(qb_container);

        var title = $(document.createElement('div'));
        title.html('3rd Party CI Scoreboard');
        title.addClass('query_box_title');
        title.appendTo(qb_div);

        var current_project = get_param_by_name('project');
        var current_user = get_param_by_name('user');
        var current_timeframe = get_param_by_name('timeframe');
        var start_date = get_param_by_name('start');
        var end_date = get_param_by_name('end');

        var form = $(document.createElement('form'));

        add_input_to_form(form, 'text', 'Project Name', 'project', current_project);
        add_input_to_form(form, 'text', 'CI Account Username', 'user', current_user);
        add_break_to_form(form);
        add_input_to_form(form, 'text', 'Timeframe (hours)', 'timeframe', current_timeframe);
        add_input_to_form(form, 'date', 'Start Date', 'start', start_date);
        add_input_to_form(form, 'date', 'End Date', 'end', end_date);
        // TODO: Implement the "start" and "count" filters so we can do pagination

        submit_button = $('<input/>', { type:'submit', value:'GO!'});
        submit_button.appendTo(form);
        form.submit(function(){
            location.href = '/' + $(this).serialize();
        });

        form.appendTo(qb_div);
    }

    board.build = function (host, container) {
        hostname = host;
        table_div_id = container;
        gather_data_and_build();
    };

    return board;
})();