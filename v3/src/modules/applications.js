const {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  StringSelectMenuBuilder,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  EmbedBuilder,
} = require('discord.js');

function init(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS application_forms (
      guild TEXT NOT NULL,
      id TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT DEFAULT '',
      questions TEXT DEFAULT '[]',
      review_channel TEXT,
      accept_role TEXT,
      deny_message TEXT DEFAULT '',
      PRIMARY KEY (guild, id)
    );

    CREATE TABLE IF NOT EXISTS applications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      guild TEXT,
      form_id TEXT,
      user TEXT,
      answers TEXT,
      status TEXT DEFAULT 'pending',
      reviewer TEXT,
      created INTEGER
    );
  `);
}

function ensureDefault(db, guild) {
  let form = db
    .prepare('SELECT * FROM application_forms WHERE guild = ? ORDER BY id LIMIT 1')
    .get(guild);

  if (!form) {
    db.prepare(
      'INSERT INTO application_forms (guild, id, title, description, questions) VALUES (?, ?, ?, ?, ?)'
    ).run(
      guild,
      'general',
      'General Application',
      'Complete the application below.',
      JSON.stringify([
        'Why do you want to join?',
        'Tell us about yourself.',
        'What can you contribute?',
      ])
    );

    form = db
      .prepare('SELECT * FROM application_forms WHERE guild = ? AND id = ?')
      .get(guild, 'general');
  }

  return form;
}

function readQuestions(form) {
  try {
    const parsed = JSON.parse(form.questions || '[]');
    return Array.isArray(parsed) ? parsed.slice(0, 5) : [];
  } catch {
    return [];
  }
}

function questionText(question) {
  return typeof question === 'string' ? question : String(question?.label || 'Question');
}

function panel(db, guild) {
  const forms = db
    .prepare('SELECT * FROM application_forms WHERE guild = ? ORDER BY title')
    .all(guild);

  const list = forms.length ? forms : [ensureDefault(db, guild)];

  return {
    embeds: [
      new EmbedBuilder()
        .setTitle('📝 Applications')
        .setDescription('Choose an application below. Each form can have its own questions and review channel.')
        .setColor(0x5865f2),
    ],
    components: [
      new ActionRowBuilder().addComponents(
        new StringSelectMenuBuilder()
          .setCustomId('application:select')
          .setPlaceholder('Choose an application')
          .addOptions(
            list.slice(0, 25).map((form) => ({
              label: String(form.title || 'Application').slice(0, 100),
              value: String(form.id),
              description: String(form.description || 'Apply now').slice(0, 100),
            }))
          )
      ),
    ],
  };
}

async function start(interaction, db, form) {
  const questions = readQuestions(form);

  if (!questions.length) {
    return interaction.reply({
      content: '❌ This application has no questions configured.',
      ephemeral: true,
    });
  }

  const modal = new ModalBuilder()
    .setCustomId(`application:submit:${form.id}`)
    .setTitle(String(form.title || 'Application').slice(0, 45));

  for (let index = 0; index < questions.length; index += 1) {
    const question = questions[index];
    const label = questionText(question).slice(0, 45) || `Question ${index + 1}`;
    const style = question && typeof question === 'object' && question.style === 'short'
      ? TextInputStyle.Short
      : TextInputStyle.Paragraph;
    const required = !(question && typeof question === 'object' && question.required === false);

    modal.addComponents(
      new ActionRowBuilder().addComponents(
        new TextInputBuilder()
          .setCustomId(`q${index}`)
          .setLabel(label)
          .setStyle(style)
          .setRequired(required)
          .setMaxLength(1000)
      )
    );
  }

  return interaction.showModal(modal);
}

async function submit(interaction, db, form) {
  const questions = readQuestions(form);
  const answers = questions.map((question, index) => ({
    question: questionText(question),
    answer: interaction.fields.getTextInputValue(`q${index}`),
  }));

  const result = db
    .prepare(
      'INSERT INTO applications (guild, form_id, user, answers, created) VALUES (?, ?, ?, ?, ?)'
    )
    .run(
      interaction.guildId,
      form.id,
      interaction.user.id,
      JSON.stringify(answers),
      Date.now()
    );

  const reviewChannel = form.review_channel
    ? interaction.guild.channels.cache.get(form.review_channel)
    : null;

  if (reviewChannel && reviewChannel.isTextBased()) {
    const embed = new EmbedBuilder()
      .setTitle(`📝 Application #${result.lastInsertRowid}`)
      .setDescription(
        `Applicant: ${interaction.user}\nForm: **${form.title}**\n\n` +
          answers.map((item) => `**${item.question}**\n${item.answer}`).join('\n\n')
      )
      .setColor(0x5865f2)
      .setTimestamp();

    await reviewChannel.send({
      embeds: [embed],
      components: [
        new ActionRowBuilder().addComponents(
          new ButtonBuilder()
            .setCustomId(`application:accept:${result.lastInsertRowid}`)
            .setLabel('Accept')
            .setStyle(ButtonStyle.Success),
          new ButtonBuilder()
            .setCustomId(`application:deny:${result.lastInsertRowid}`)
            .setLabel('Deny')
            .setStyle(ButtonStyle.Danger),
          new ButtonBuilder()
            .setCustomId(`application:hold:${result.lastInsertRowid}`)
            .setLabel('Hold')
            .setStyle(ButtonStyle.Secondary)
        ),
      ],
    });
  }

  return interaction.reply({
    content: '✅ Application submitted successfully.',
    ephemeral: true,
  });
}

async function handle(interaction, ctx) {
  const { db } = ctx;

  if (interaction.isStringSelectMenu() && interaction.customId === 'application:select') {
    const form = db
      .prepare('SELECT * FROM application_forms WHERE guild = ? AND id = ?')
      .get(interaction.guildId, interaction.values[0]);

    if (!form) {
      return interaction.reply({ content: '❌ Application no longer exists.', ephemeral: true });
    }

    return start(interaction, db, form);
  }

  if (interaction.isButton() && interaction.customId === 'application:open') {
    return start(interaction, db, ensureDefault(db, interaction.guildId));
  }

  if (interaction.isModalSubmit() && interaction.customId.startsWith('application:submit:')) {
    const formId = interaction.customId.split(':').slice(2).join(':');
    const form = db
      .prepare('SELECT * FROM application_forms WHERE guild = ? AND id = ?')
      .get(interaction.guildId, formId);

    if (!form) {
      return interaction.reply({ content: '❌ Application no longer exists.', ephemeral: true });
    }

    return submit(interaction, db, form);
  }

  if (interaction.isButton() && interaction.customId.startsWith('application:')) {
    const [, action, id] = interaction.customId.split(':');

    if (!['accept', 'deny', 'hold'].includes(action)) return false;

    db.prepare('UPDATE applications SET status = ?, reviewer = ? WHERE id = ?').run(
      action,
      interaction.user.id,
      id
    );

    return interaction.reply(`Application #${id}: **${action}** by ${interaction.user}.`);
  }

  return false;
}

module.exports = { init, ensureDefault, panel, handle };