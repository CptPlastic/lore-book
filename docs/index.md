<div class="legacy-home">
	<canvas id="sparkles" aria-hidden="true"></canvas>

	<div class="page">
		<header class="cover">
			<div class="sigil">📜</div>
			<h1>Lore</h1>
			<p class="subtitle">Keeper of the Chronicle</p>
			<p class="tagline">The spellbook for your codebase: chronicle decisions, context, and lessons your AI companions can actually read.</p>
		</header>

		<section class="parchment">
			<h2><span class="rune">✦</span> What is Lore?</h2>
			<p>AI coding tools are stateless. They do not remember why you chose PostgreSQL over SQLite, which safety rules cannot be bypassed, or what tradeoffs already shaped this codebase.</p>
			<p><strong>Lore</strong> fixes that. It is a local AI memory system for software projects. You capture knowledge once as plain files alongside your code, then export it into instruction files your tools can read automatically.</p>
			<p>No external database. No API keys. No cloud sync. Everything lives in <code>.lore/</code> next to your repo.</p>
			<div class="badge-row">
				<span class="ver-badge">LOCAL YAML STORE</span>
				<span class="ver-badge">CHRONICLE FIRST</span>
				<span class="ver-badge">NO CLOUD SYNC</span>
				<span class="ver-badge">TOOL-AGNOSTIC</span>
			</div>
		</section>

		<section class="parchment">
			<h2><span class="rune">⚜</span> The Three Artefacts</h2>

			<h3>Spell</h3>
			<p>A single piece of knowledge: a decision, a fact, a hard-won lesson, or a preference worth preserving.</p>

			<h3>Tome</h3>
			<p>A named collection of spells. Default tomes include <code>decisions</code>, <code>facts</code>, <code>preferences</code>, and <code>summaries</code>.</p>

			<h3>Relic</h3>
			<p>A raw artifact saved as-is for later distillation. Use relics when things are moving too fast to curate carefully in the moment.</p>
		</section>

		<section class="parchment">
			<h2><span class="rune">✧</span> How the Magic Flows</h2>
			<div class="scroll-diagram">Your decisions, facts and lessons
				↓  lore add / lore relic
	.lore/  (plain YAML)
				↓  lore export
CHRONICLE.md  ←  full project memory
				↓  referenced by lean adapters
Copilot · Claude · Cursor · AGENTS · prompts
				↓
Every AI tool reads your repo context</div>
		</section>

		<section class="parchment">
			<h2><span class="rune">✶</span> First Invocation</h2>
			<p>Start with onboarding. Lore walks through store setup, your first memory entry, and export flow in one guided ritual.</p>
			<div class="incantation">lore onboard</div>
			<ol class="ritual-steps">
				<li><strong>Initialize the spellbook</strong> with a project description and local defaults.</li>
				<li><strong>Record real knowledge</strong> as decisions, facts, preferences, or summaries.</li>
				<li><strong>Export the chronicle</strong> so every supported AI tool inherits the same context.</li>
				<li><strong>Enable semantic search</strong> later with <code>lore setup semantic</code> if you want dense embeddings.</li>
			</ol>
			<div class="note">Requirements: Python 3.10+. Dense vector search is optional. Lore falls back to TF-IDF when needed.</div>
		</section>

		<section class="parchment">
			<h2><span class="rune">⌘</span> Start Here</h2>
			<div class="target-list">
				<div class="target-item">
					  <strong><a href="install/">Install</a></strong>
					Setup instructions for PyPI, local development, and semantic search extras.
				</div>
				<div class="target-item">
					  <strong><a href="concepts/">Core Concepts</a></strong>
					Understand spells, tomes, relics, and the chronicle model.
				</div>
				<div class="target-item">
					  <strong><a href="cli/">CLI Reference</a></strong>
					Learn the primary commands for capture, search, and export.
				</div>
				<div class="target-item">
					  <strong><a href="faq/">FAQ</a></strong>
					Short answers to common questions about storage, AI tools, and workflow.
				</div>
			</div>
		</section>

		<section class="parchment">
			<h2><span class="rune">🜏</span> Incantations</h2>

			<h3>Install via pip</h3>
			<div class="incantation">pip install lore-book</div>

			<h3>Local development</h3>
			<div class="incantation">pip install -e .</div>

			<h3>Cast your first spells</h3>
			<div class="incantation">lore add decisions "Use PostgreSQL for row-level locking"
lore add facts "Auth service is the sole issuer of JWTs"
lore export</div>
		</section>

		<section class="parchment">
			<h2><span class="rune">📖</span> Grimoire of Commands</h2>
			<div class="command-columns">
				<div class="command-item">
					<strong>Store</strong>
					<p><code>lore onboard</code>, <code>lore init</code>, <code>lore add</code>, <code>lore list</code>, <code>lore remove</code></p>
				</div>
				<div class="command-item">
					<strong>Search</strong>
					<p><code>lore search &lt;query&gt;</code>, <code>lore index rebuild</code>, <code>lore setup semantic</code></p>
				</div>
				<div class="command-item">
					<strong>Relics</strong>
					<p><code>lore relic capture</code>, <code>lore relic list</code>, <code>lore relic view</code>, <code>lore relic distill</code></p>
				</div>
				<div class="command-item">
					<strong>Publishing</strong>
					<p><code>lore export</code>, <code>lore export --format prompt</code>, <code>lore config &lt;key&gt; &lt;value&gt;</code></p>
				</div>
			</div>
			<div class="links">
				<a class="link-rune" href="https://github.com/CptPlastic/lore-book">✦ Source Repository</a>
				<a class="link-rune" href="https://pypi.org/project/lore-book/">⚜ PyPI Package</a>
			</div>
		</section>

		<div class="divider">— ✦ — ✦ — ✦ —</div>

		<footer>
			LORE · CANONICAL DOCUMENTATION · FSL-1.1-MIT
		</footer>
	</div>
</div>
