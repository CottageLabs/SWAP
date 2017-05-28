
$.fn.holder.use.swap = {
  url: "https://swapsurvey.org/query/student/_search",
  pushstate: false,
  sticky:true,
  record:false,
  size:10000,
  display:['swap','filters','graph','sankey','scotland'],
  fields: ['classification','gender','college','campus','disability','archive','situation','profilegrades','progresswhere', 'simd_quintile','progressions.1st_year_result','progressions.reg_1st_year','nationality','locale','date_of_birth','last_name'],
  facets: {
    archive: { terms: { field: "archive.exact", size: 100, order: "reverse_term" } },
    locale: { terms: { field: "locale.exact" } },
    gender: { terms: { field: "gender.exact" } },
    "post code": { terms: { field: "post_code", size: 1500 } },
    simd_quintile: { terms: { field: "simd_quintile.exact" } },
    disability: { terms: { field: "disability.exact", "size": 100 } },
    "registered disabled": { terms: { field: "registered_disabled" } },
    situation: { terms: { field: "situation.exact" } },
    nationality: { terms: { field: "nationality.exact" } },
    college: { terms: { field: "college.exact", "size": 100 } },
    campus: { terms: { field: "campus.exact", "size": 100 } },
    course: { terms: { field: "course.exact", "size": 100 } },
    classification: { terms: { field: "classification.exact", "size": 100 } },
    progression: { terms: { field: "progresswhere.exact", "size": 100 } },
    "date of birth": { terms: { field: "date_of_birth.exact", "size": 100 } },
    "last name": { terms: { field: "last_name.exact", "size": 100 } }
  }  
};

$.fn.holder.display.swap = function(obj) {
  var options = obj.holder.options;
  if (options.paging) return;
  
  var swapheadertemplate = '\
  <div class="row" id="swapheader" style="margin-top:-10px;">\
    <div class="col-md-12">\
      <h1 style="font-size:54px;text-align:center;">SWAP reporting</h1>\
      <p style="text-align:center;"><a href="/admin">Click here to go back to SWAP admin</a></p>\
    </div>\
  </div>\
  \
  <div class="row">\
    <div class="col-md-12">\
      <div class="well">\
        <ol>\
          <li>\
            Start by selecting any relevant overall filters and/or type in a search term (these can also be added or removed at any time).\
            <br>The chosen filters will update the headline statistics, and the records available for graphing and visualisation.\
          </li>\
          <li>Then choose which key values and years to graph.</li>\
          <li>\
            Next, visualise and compare the flow of students through up to five key stages - less stages gives \
            a simpler picture, but more stages can sometimes work well too, depending on the filters and stages chosen.\
          </li>\
          <li>\
            Finally, map the starting locations of students to college destinations. \
            Blue circles are campuses, red circles are home post codes, larger circles indicate more \
            students from/to a location. This works best when applying overall filters, e.g. filter by \
            registered disabled then by college to see how far disabled students live from their college. \
            You can directly filter by the campus and post code circles on the map by clicking on them. \
            Double-click or scroll on the map to zoom in to relevant areas.\
          </li>\
        </ol>\
      </div>\
    </div>\
  </div>';

  var swapoverviewtemplate = '\
  <div class="row">\
    <div class="col-md-12">\
      <div class="well" style="margin-bottom:0px;">\
        <h2 id="overview"></h2>\
        <h2>\
          <span id="period">Across all periods</span> <span id="inlocale">there were</span> <span class="label label-swap" id="total"></span> student registrations.\
        </h2>\
        <h2>\
          * <span class="label label-swap" id="males"></span> were male, and \
          <span class="label label-swap" id="females"></span> were female.\
        </h2>\
        <h2>\
          * Most were <span class="label label-swap" id="situation"></span>, \
          <span class="label label-swap" id="nationality"></span>,\
          staying in <span class="label label-swap" id="post_code"></span>.\
        </h2>\
        <h2>\
          * <span class="label label-swap" id="disability"></span> listed some form of disability, with \
          <span class="label label-swap" id="regd_disabled"></span> registered disabled.\
        </h2>\
        <h2>\
          * The most popular course was <span class="label label-swap" id="pcourse"></span>  \
          with <span class="label label-swap" id="pcoursen"></span> students.\
        </h2>\
        <h2>\
          * The most common college was <span class="label label-swap" id="pcollege"></span>  \
          with <span class="label label-swap" id="pcollegen"></span> students.\
        </h2>\
      </div>\
    </div>\
  </div>';

  if ( !$('#swapheader').length ) {
    obj.parent().before(swapheadertemplate);
    $('.'+options.class+'.default').after(swapoverviewtemplate);
    $('.'+options.class+'.options').show();
  }
  
  var data = options.response;

  $('#total').text(data.hits.total);

  $('#disability').text('0');
  $('#regd_disabled').text('0');
  $('#pcourse').text('0');
  $('#pcoursen').text('0');
  $('#pcollege').text('0');
  $('#pcollegen').text('0');
  $('#situation').text('0');
  $('#nationality').text('0');
  $('#post_code').text('0');
  $('#males').text('0');
  $('#females').text('0');

  for ( var r in data.facets.disability.terms ) {
    if ( data.facets.disability.terms[r].term === "No known disability" ) {
      $('#disability').text(data.hits.total - data.facets.disability.terms[r].count - data.facets.disability.missing);
    }
  }

  for ( var r in data.facets["registered disabled"].terms ) {
    if ( data.facets["registered disabled"].terms[r].term === "true" ) {
      $('#regd_disabled').text(data.facets["registered disabled"].terms[r].count);
    }
  }

  try {
    $('#pcourse').text(data.facets.course.terms[0].term);
    $('#pcoursen').text(data.facets.course.terms[0].count);
  } catch(err) {}
  try {
    $('#pcollege').text(data.facets.college.terms[0].term);
    $('#pcollegen').text(data.facets.college.terms[0].count);
  } catch(err) {}

  try {
    $('#situation').text(data.facets.situation.terms[0].term + ' (' + data.facets.situation.terms[0].count + ')');
  } catch(err) {}
  try {
    $('#nationality').text(data.facets.nationality.terms[0].term + ' (' + data.facets.nationality.terms[0].count + ')');
  } catch(err) {}
  try {
    $('#post_code').text(data.facets["post code"].terms[0].term + ' (' + data.facets["post code"].terms[0].count + ')');
  } catch(err) {}

  if ( data.facets.archive.terms.length === 1 ) {
    $('#period').html('In the <span class="label label-swap">' +  data.facets.archive.terms[0].term + '</span> period');
  } else {
    $('#period').html('Across all periods');      
  }

  if ( data.facets.locale.terms.length === 1 ) {
    $('#inlocale').html('<span class="label label-swap">SWAP ' + data.facets.locale.terms[0].term + '</span> had');
  } else {
    $('#inlocale').html('there were');
  }

  for ( var r in data.facets.gender.terms ) {
    if ( data.facets.gender.terms[r].term === "Male" ) {
      $('#males').text(data.facets.gender.terms[r].count);
    }
    if ( data.facets.gender.terms[r].term === "Female" ) {
      $('#females').text(data.facets.gender.terms[r].count);
    }
  }

  $('#overview').html('');
  try {
    var hasoverview = false;
    var overview = 'Report filtered for ';
    for ( var q in $('body').holder.options.query.query.filtered.filter.bool.must ) {
      var qq = $('body').holder.options.query.query.filtered.filter.bool.must[q].term;
      for ( var qqp in qq ) {
        if ( qqp !== 'archive.exact' && qqp !== 'locale.exact' ) {
          overview += '<span class="label label-swap">' + qqp.replace('.exact','').replace('_',' ') + ': ' + qq[qqp] + '</span> ';
          hasoverview = true;
        }
      }
    }
    if (hasoverview) $('#overview').html(overview + '.');
  } catch(err) {}
  
}
