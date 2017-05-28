
$.fn.holder.display.filters = function(obj) {
  var options = obj.holder.options;
  if (options.paging) return; // when paging the results, filters don't change, and by default won't even get re-queried, so no point doing anything
  
  if ( !$('.'+options.class+'.filters').length ) obj.prepend('<div class="' + options.class + ' display filters"></div>');
  if ( options.response && ( options.response.facets || options.response.aggs || options.response.aggregations ) ) {
    // assume an ES options.response exists, and extract facets from it
    // or do this as part of default, and just look for options.filters here?
    // also note - if paging/scrolling, will facets change? They should not.
    options.filters = {};
    // also for ES, there could be facets or aggregations (or aggs) - look for both
    if (options.response.aggregations) options.response.aggs = options.response.aggregations
    if (options.response.aggs) {
      for ( var a in options.response.aggs ) {
        var agg = options.response.aggs[a];
        if (agg.buckets) {
          if (options.filters[a] === undefined) options.filters[a] = [];
          for ( var b in agg.buckets ) {
            var bucket = agg.buckets[b];
            if ( bucket.key && bucket.doc_count ) {
              var field = options.query.aggs ? options.query.aggs[a].terms.field : options.query.aggregations[a].terms.field;
              options.filters[a].push({name:a,field:field,key:bucket.key,value:bucket.doc_count});
            }
          }
        }
      }        
    } else if ( options.response.facets) {
      for ( var f in options.response.facets ) {
        var facet = options.response.facets[f];
        if (facet.terms) {
          if (options.filters[f] === undefined) options.filters[f] = [];
          for ( var t in facet.terms ) {
            var term = facet.terms[t];
            if ( term.term !== undefined && term.count !== undefined ) {
              var fieldname = options.query.facets[f].terms.field;
              options.filters[f].push({name:f,field:fieldname,key:term.term,value:term.count});
            }
          }
        }
      }
    }
  }
  if (!options.filters) options.filters = {};

  if ( $('.'+options.class+'.filters').length ) {
    $('.'+options.class+'.filters').html("");
    var fs = 0;
    for ( var o in options.filters ) fs += 1;
    var colw = fs % 4 === 0 ? '3' : '4';
    for ( var ff in options.filters ) {
      if ( options.filters[ff].length ) {
        var disp = '<div class="col-md-' + colw + '"><select style="margin-bottom:3px;" class="form-control holder" do="add" key="';
        disp += options.filters[ff][0].field;
        disp += '"><option value="">filter by ' + ff + '</option>';
        for ( var fv in options.filters[ff] ) {
          disp += '<option value="' + options.filters[ff][fv].key + '">' + options.filters[ff][fv].key + ' (' + options.filters[ff][fv].value + ')</option>';
        }
        disp += '</select></div>';
        $('.' + options.class + '.filters').append(disp);
      }
    }
  }
}
  

