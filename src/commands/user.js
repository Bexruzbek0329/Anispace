export const userCommands = {
  async start(bot, msg, supabase) {
    const { data: user } = await supabase
      .from('users')
      .insert([
        {
          user_id: msg.from.id,
          username: msg.from.username,
          first_name: msg.from.first_name,
          last_name: msg.from.last_name
        }
      ])
      .select()
      .single();

    const welcomeMessage = `
Assalomu alaykum, ${msg.from.first_name}!
Anime botimizga xush kelibsiz!

/animelist - Barcha animalar ro'yxati
/vip - VIP status tekshirish
    `;

    bot.sendMessage(msg.chat.id, welcomeMessage);
  },

  async checkVip(bot, msg, supabase) {
    const { data: user } = await supabase
      .from('users')
      .select('is_vip')
      .eq('user_id', msg.from.id)
      .single();

    const message = user?.is_vip
      ? "Siz VIP foydalanuvchisiz! 🌟"
      : "Siz oddiy foydalanuvchisiz. VIP status olish uchun admin bilan bog'laning.";

    bot.sendMessage(msg.chat.id, message);
  }
};