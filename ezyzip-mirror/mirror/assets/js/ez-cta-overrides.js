/*
 * Pro-link CTA classification override - deliberately EMPTY.
 *
 * views/layout/fragment/proLinkTracking.ftl.html classifies every click on an
 * ezyzip.pro link into a placement id. That classifier is inline in the page,
 * so changing it costs a full site rebuild (buildall.sh: 7 scripts x 16
 * languages). This file is the escape hatch: it lives under assets/, which
 * buildall.sh rsyncs on its own, so it can be corrected and deployed in
 * seconds without a rebuild.
 *
 * Use it when GA4 shows a non-empty 'unknown' bucket (its event_label carries
 * the path) or a placement is obviously misattributed. Define:
 *
 *   window.EZ_CTA_OVERRIDE = function (anchor, placement) {
 *       // return a new placement id, or a falsy value to keep `placement`
 *       if (placement === 'unknown' && anchor.closest('.some-new-widget')) {
 *           return 'some-new-widget';
 *       }
 *   };
 *
 * The tracker reads this at CLICK time, so loading it with `defer` is fine.
 * Throwing here is safe - the tracker catches and keeps its own answer.
 *
 * After deploying a change, purge /assets/js/ez-cta-overrides.js by URL in
 * Cloudflare: the file carries no cache-busting token (adding one would need
 * the rebuild this hatch exists to avoid).
 *
 * Fold any override that proves correct back into proLinkTracking.ftl.html on
 * the next rebuild, and add the placement to
 * SERP-Analysis/config/pro_link_placements.json so the dashboard can show its
 * zeros.
 */
