import csv, json, unittest
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FullLeagueGateTests(unittest.TestCase):
    def test_verified_youtube_registry_covers_32_clubs(self):
        with (ROOT/'config/official_channel_registry.csv').open() as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(len(rows),32)
        self.assertEqual(len({r['club_id'] for r in rows}),32)
        self.assertTrue(all(r['evidence_status']=='confirmed' and r['official_channel_id'].startswith('UC') for r in rows))
        videos=json.loads((ROOT/'data/curated/content_video.json').read_text())
        manifest=json.loads((ROOT/'data/manifests/youtube_complete_acquisition.json').read_text())
        self.assertEqual(manifest['completed_clubs'],32)
        self.assertEqual(len(manifest['results']),32)
        self.assertTrue(all(row['evidence_status']=='confirmed' for row in manifest['results']))
        self.assertTrue(all(
            row['playlist_video_ids']==row['accessible_videos']+row['inaccessible_or_deleted_videos']
            and row['playlist_pages']>0 and row['video_detail_pages']>0
            and row['uploads_playlist_id'].startswith('UU')
            for row in manifest['results']
        ))
        self.assertEqual(len(videos),sum(row['accessible_videos'] for row in manifest['results']))
        self.assertEqual(len(videos),len({(row['club_id'],row['video_id']) for row in videos}))
        self.assertEqual({r['club_id'] for r in videos},{r['club_id'] for r in rows})
        required={'video_id','channel_id','published_at','title','description','duration','view_count','like_count','comment_count','retrieved_at'}
        self.assertTrue(all(required.issubset(video) for video in videos))

    def test_no_preseason_moments_enter_analysis(self):
        games={row['game_id']:row for row in json.loads((ROOT/'data/curated/game.json').read_text())}
        moments=json.loads((ROOT/'data/curated/moment.json').read_text())
        events=json.loads((ROOT/'data/curated/game_event.json').read_text())
        windows=json.loads((ROOT/'data/curated/attention_event_window.json').read_text())
        self.assertTrue(all(games[row['game_id']]['game_type'] in {2,3} for row in moments if row.get('game_id')))
        self.assertTrue(all(games[row['game_id']]['game_type'] in {2,3} for row in events))
        self.assertTrue(all(games[row['game_id']]['game_type'] in {2,3} for row in windows if row.get('game_id')))

    def test_market_context_covers_every_club(self):
        rows=json.loads((ROOT/'data/curated/market_context.json').read_text())
        self.assertEqual(len({r['club_id'] for r in rows}),32)
        for club in {r['club_id'] for r in rows}:
            metrics={r['metric_name'] for r in rows if r['club_id']==club and r['evidence_status']=='confirmed'}
            self.assertIn('population',metrics)

    def test_qcew_lqs_keep_complete_denominator_vector(self):
        rows=json.loads((ROOT/'data/curated/market_context.json').read_text())
        confirmed=[r for r in rows if r['metric_name'].startswith('qcew_lq_') and r['evidence_status']=='confirmed']
        self.assertTrue(confirmed)
        self.assertTrue(all(all(r['denominator_vector'].get(k) is not None for k in ('market_industry_employment','market_total_employment','us_industry_employment','us_total_employment')) for r in confirmed))

    def test_acs_fallback_completes_preferred_us_industry_coverage(self):
        rows=json.loads((ROOT/'data/curated/market_context.json').read_text())
        preferred=[r for r in rows if r['metric_name'].startswith('preferred_industry_lq_')]
        qcew=[r for r in rows if r['metric_name'].startswith('qcew_lq_')]
        acs=[r for r in rows if r['metric_name'].startswith('acs_industry_lq_')]
        self.assertEqual(len(preferred),250)
        self.assertTrue(all(r['evidence_status']=='confirmed' and r['metric_value'] is not None for r in preferred))
        self.assertEqual(sum(r['fallback_used'] for r in preferred),36)
        self.assertEqual(sum(r['evidence_status']=='unavailable' for r in qcew),36)
        self.assertTrue(all(r.get('unavailable_reason')=='bls_confidentiality_suppression' for r in qcew if r['evidence_status']=='unavailable'))
        self.assertEqual(len(acs),250)
        self.assertTrue(all(r['margin_of_error_inputs']['market_industry_moe_90'] is not None for r in acs))

    def test_hierarchical_model_converged_and_suppresses_small_samples(self):
        model=json.loads((ROOT/'data/curated/club_moment_estimate.json').read_text())
        self.assertEqual(model['model_version'],'2.0.0-unbalanced-multichannel-hierarchical')
        self.assertEqual(model['status'],'confirmed')
        self.assertTrue(model['converged'])
        self.assertEqual(set(model['channels']),{'wikimedia_pageviews','gdelt_earned_media'})
        self.assertEqual(len(model['channel_models']),2)
        self.assertTrue(all(channel['converged'] for channel in model['channel_models']))
        self.assertTrue(all(set(channel['sensitivity_estimates'])=={'7','21'} for channel in model['channel_models']))
        self.assertTrue(all(not row['ranking_eligible'] for row in model['estimates'] if row['sample_size']<10))
        self.assertTrue(all(
            row['stable'] == (row['cross_channel_status'] in {'stable_positive','stable_negative'})
            for row in model['cross_channel_assessments']
        ))
        self.assertTrue(all(
            not row['stable'] or row['rule']=='both channels have at least 10 modeled and 10 isolated observations; modeled and club-local raw medians share direction across channels; every modeled and raw 95% interval excludes zero'
            for row in model['cross_channel_assessments']
        ))

    def test_gdelt_manual_audit_is_complete(self):
        with (ROOT/'data/evidence/gdelt_article_audit.csv').open() as handle:
            audit=list(csv.DictReader(handle))
        self.assertGreaterEqual(len(audit),160)
        self.assertEqual(len({r['club_id'] for r in audit}),32)
        self.assertTrue(all(r['reviewer'] and r['is_true_club_match'] in {'true','false'} and r['reviewed_at'] for r in audit))
        precision=json.loads((ROOT/'data/curated/gdelt_gkg_release_precision.json').read_text())
        self.assertEqual(precision['clubs_eligible_for_quantification'],32)
        self.assertGreaterEqual(precision['active_extraction_reviewed_articles'],160)
        self.assertEqual(precision['ineligible_clubs'],[])
        self.assertTrue(all(
            state['quantification_status']=='confirmed'
            and state['sample_size']>=5 and state['precision']>=.90
            for state in precision['club_precision'].values()
        ))

    def test_gdelt_daily_panel_is_complete_and_audited(self):
        rows=json.loads((ROOT/'data/curated/gdelt_gkg_attention_daily.json').read_text())
        manifest=json.loads((ROOT/'data/manifests/gdelt_gkg_release_acquisition.json').read_text())
        self.assertIn(manifest['evidence_status'],{'confirmed','confirmed_with_visible_source_gaps'})
        self.assertEqual(manifest['daily_rows'],len(rows))
        self.assertEqual(manifest['club_identity_count'],33)
        self.assertEqual(manifest['current_clubs_eligible_for_quantification'],32)
        self.assertTrue(all(
            (row['metric_value'] is not None and row['normalized_articles_per_100k'] is not None)
            or row['evidence_quality']=='unavailable_source_partition_gap'
            for row in rows
        ))

    def test_gdelt_gkg_remains_excluded_when_club_precision_fails(self):
        manifest=json.loads((ROOT/'data/manifests/gdelt_gkg_acquisition.json').read_text())
        precision=json.loads((ROOT/'data/curated/gdelt_gkg_precision.json').read_text())
        supplement=json.loads((ROOT/'data/manifests/gdelt_gkg_archive_supplement.json').read_text())
        self.assertEqual(manifest['evidence_status'],'confirmed_daily_panel_but_not_release_eligible_due_club_precision')
        self.assertEqual(precision['status'],'audit_complete')
        self.assertEqual(supplement['evidence_status'],'manual_review_complete')
        self.assertEqual(supplement['reviewed_candidates'],87)
        self.assertGreater(supplement['false_matches'],0)
        self.assertEqual(precision['reviewed_articles'],257)
        self.assertEqual(precision['clubs_eligible_for_quantification'],28)
        self.assertEqual(precision['ineligible_clubs'],['BOS','CHI','NSH','WPG'])
        self.assertEqual(manifest['excluded_diagnostic_output'],'data/curated/gdelt_gkg_attention_daily_excluded.json')
        self.assertTrue(all(
            r['evidence_quality']!='confirmed_for_quantified_modeling'
            for r in json.loads((ROOT/manifest['excluded_diagnostic_output']).read_text())
        ))
        release=json.loads((ROOT/'data/manifests/gdelt_gkg_release_acquisition.json').read_text())
        self.assertEqual(release['recovered_clubs'],['BOS','CHI','NSH','WPG'])
        self.assertNotEqual(release['query_checksum'],manifest['query_checksum'])

    def test_sourced_rivalries_cover_all_current_clubs(self):
        with (ROOT/'config/rivalries.csv').open() as handle:
            rows=list(csv.DictReader(handle))
        clubs={row['club_id'] for row in rows}|{row['opponent_id'] for row in rows}
        self.assertEqual(len(clubs),32)
        self.assertEqual(len(rows),len({tuple(sorted((row['club_id'],row['opponent_id']))) for row in rows}))
        self.assertTrue(all(
            row['club_id']!=row['opponent_id'] and row['rule_version']=='1.1.0'
            and row['valid_from'] and row['source_note'] and row['evidence_status']=='confirmed'
            and row['source_url'].startswith('https://') for row in rows
        ))

if __name__=='__main__': unittest.main()
