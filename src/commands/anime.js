export const animeCommands = {
  async addAnime(bot, msg, supabase) {
    const isAdmin = await checkAdmin(msg.from.id, supabase);
    if (!isAdmin) return;

    // Implementation for adding new anime
  },

  async listAnimes(bot, msg, supabase) {
    const { data: animes } = await supabase
      .from('animes')
      .select('*');

    let message = "📺 Anime ro'yxati:\n\n";
    for (const anime of animes) {
      message += `${anime.name} (${anime.season}-fasl)\n`;
    }

    bot.sendMessage(msg.chat.id, message);
  },

  async showEpisodes(bot, msg, supabase) {
    // Implementation for showing anime episodes
  }
};

async function checkAdmin(userId, supabase) {
  const { data } = await supabase
    .from('admins')
    .select('*')
    .eq('user_id', userId)
    .single();
  
  return !!data;
}