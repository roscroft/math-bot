using JuMP, Gurobi
include("./vision.jl")

function solve_tower(n_max, top, right, bottom, left)
    println("N: ",n_max)
    println("Top: ",top)
    println("Right: ",right)
    println("Bottom: ",bottom)
    println("Left: ",left)
    const ineqs = coefficients(n_max)

    model = Model(solver=GurobiSolver())
    @variable(model, 1 <= x[1:n_max, 1:n_max] <= n_max, Int)
    @variable(model, b[1:n_max, 1:n_max, 1:n_max], Bin)
    @constraint(model, [i=1:n_max, j=1:n_max], x[i,j] == sum(k*b[i,j,k] for k = 1:n_max))
    @constraint(model, [i=1:n_max, k=1:n_max], sum(b[i,j,k] for j=1:n_max) == 1)
    @constraint(model, [j=1:n_max, k=1:n_max], sum(b[i,j,k] for i=1:n_max) == 1)
    println("Model created.")
    #= println(model) =#
    for idx in 1:n_max
        top_set = ineqs[top[idx]]
        bot_set = ineqs[bottom[idx]]
        left_set = ineqs[left[idx]]
        right_set = ineqs[right[idx]]
        # Top
        @constraint(model, top_set["A"]*x[:,idx] .<= top_set["b"])
        @constraint(model, bot_set["A"]*x[end:-1:1,idx] .<= bot_set["b"])
        @constraint(model, left_set["A"]*x[idx,:] .<= left_set["b"])
        @constraint(model, right_set["A"]*x[idx,end:-1:1] .<= right_set["b"])
    end
    println("All constraints added.")
    solve(model)
    soln = convert.(Int64, getvalue(x))
    output = ""
    for idx = 1:n_max
        output = string(output, "\n",soln[idx,:])
    end
    return output
end
