namespace ANDROID_R76;

/// <summary>First-party deterministic port of R75 accepted tile-motion rules.</summary>
public sealed class MazeLogic
{
    public const int Width = 8;
    public const int Height = 8;
    public const int GoalX = 6;
    public const int GoalY = 6;
    private static readonly HashSet<string> Walls = new(StringComparer.Ordinal)
    {
        "2:1","2:2","2:3","3:3","4:3","5:1","5:2",
        "0:5","1:5","2:5","4:5","5:5"
    };
    public int X { get; private set; } = 1;
    public int Y { get; private set; } = 1;
    public int Steps { get; private set; }
    public bool Won => X == GoalX && Y == GoalY;
    public static bool IsWall(int x,int y) => Walls.Contains($"{x}:{y}");
    public void Reset() { X=1;Y=1;Steps=0; }
    public void Restore(int x,int y,int steps)
    {
        if (x is < 0 or >= Width || y is < 0 or >= Height ||
            IsWall(x,y) || steps < 0)
            throw new ArgumentOutOfRangeException(nameof(x));
        X=x;Y=y;Steps=steps;
    }
    public bool Move(string direction)
    {
        if (Won)return false;
        (int dx,int dy) = direction switch
        {
            "N" => (0,-1), "S" => (0,1), "W" => (-1,0), "E" => (1,0),
            _ => (0,0)
        };
        if(dx==0 && dy==0)return false;
        int nx=X+dx,ny=Y+dy;
        if(nx<0||ny<0||nx>=Width||ny>=Height||IsWall(nx,ny))return false;
        X=nx;Y=ny;Steps++;return true;
    }
}
