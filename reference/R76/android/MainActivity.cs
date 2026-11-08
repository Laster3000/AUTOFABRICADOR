using Android.App;
using Android.OS;
using Android.Views;
using Android.Widget;
using Android.Graphics;
using Android.Content;

namespace ANDROID_R76;

[Activity(Label = "AUTOFABRICADOR R76 - Labyrinth", MainLauncher = true,
    Exported = true, Theme = "@android:style/Theme.Material.NoActionBar")]
public sealed class MainActivity : Activity
{
    private readonly MazeLogic _logic = new();
    private TextView _label = null!;
    private MazeCanvas _board = null!;
    private ISharedPreferences _prefs = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        _prefs = GetSharedPreferences("af_r76_labyrinth",FileCreationMode.Private)!;
        try
        {
            _logic.Restore(_prefs.GetInt("x",1),_prefs.GetInt("y",1),
                _prefs.GetInt("steps",0));
        }
        catch(ArgumentOutOfRangeException)
        {
            _logic.Reset();
        }
        var root = new LinearLayout(this)
        {
            Orientation=Orientation.Vertical
        };
        root.SetBackgroundColor(Android.Graphics.Color.Rgb(10,19,32));
        root.SetPadding(16,18,16,18);
        var title=new TextView(this)
        {
            Text="AUTOFABRICADOR · Labyrinth 2D",
            TextSize=21
        };
        title.SetTextColor(Android.Graphics.Color.Rgb(177,242,218));
        root.AddView(title);
        _label=new TextView(this){TextSize=16};
        _label.SetTextColor(Android.Graphics.Color.White);
        root.AddView(_label);
        _board=new MazeCanvas(this,_logic);
        root.AddView(_board,new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MatchParent, 0,1));
        var actions=new LinearLayout(this){Orientation=Orientation.Horizontal};
        foreach(var item in new[]{("↑","N"),("←","W"),("↓","S"),("→","E")})
        {
            var button=new Button(this){Text=item.Item1};
            string movement=item.Item2;
            button.Click+=(_,_)=>{_logic.Move(movement);Save();Refresh();};
            actions.AddView(button,new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WrapContent,1));
        }
        root.AddView(actions);
        var reset=new Button(this){Text="Reiniciar partida"};
        reset.Click+=(_,_)=>{_logic.Reset();Save();Refresh();};
        root.AddView(reset);
        SetContentView(root);
        Refresh();
    }
    private void Save()
    {
        using(var editor=_prefs.Edit())
        {
            editor.PutInt("x",_logic.X);
            editor.PutInt("y",_logic.Y);
            editor.PutInt("steps",_logic.Steps);
            editor.Commit();
        }
    }
    private void Refresh()
    {
        _label.Text=_logic.Won?"¡Objetivo conseguido! · Pasos: "+_logic.Steps:
          "Encuentra la estrella · Pasos: "+_logic.Steps;
        _board.Invalidate();
    }

    private sealed class MazeCanvas : View
    {
        private readonly MazeLogic _logic;
        private readonly Paint _paint=new(PaintFlags.AntiAlias);
        public MazeCanvas(Context context,MazeLogic logic):base(context)
        {
            _logic=logic;SetLayerType(LayerType.Software,null);
        }
        protected override void OnDraw(Canvas? canvas)
        {
            base.OnDraw(canvas);
            if(canvas is null)return;
            float length=Math.Min(Width,Height)-4;
            float cell=length/MazeLogic.Width;
            float left=(Width-length)/2,top=(Height-length)/2;
            canvas.DrawColor(Android.Graphics.Color.Rgb(8,24,39));
            for(int y=0;y<MazeLogic.Height;y++)
            for(int x=0;x<MazeLogic.Width;x++)
            {
                _paint.Color=MazeLogic.IsWall(x,y)?
                    Android.Graphics.Color.Rgb(80,112,130):
                    (x+y)%2==0?Android.Graphics.Color.Rgb(19,44,64):
                    Android.Graphics.Color.Rgb(16,38,57);
                canvas.DrawRect(left+x*cell+1,top+y*cell+1,
                    left+(x+1)*cell-1,top+(y+1)*cell-1,_paint);
            }
            _paint.Color=Android.Graphics.Color.Rgb(255,211,108);
            canvas.DrawCircle(left+(MazeLogic.GoalX+.5f)*cell,
                top+(MazeLogic.GoalY+.5f)*cell,cell*.25f,_paint);
            _paint.Color=Android.Graphics.Color.Rgb(148,243,213);
            canvas.DrawCircle(left+(_logic.X+.5f)*cell,
                top+(_logic.Y+.5f)*cell,cell*.32f,_paint);
        }
    }
}
